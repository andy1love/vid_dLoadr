#!/usr/bin/env python3
"""
Standalone SSH Connection Module
Provides SSH connection functionality for remote command execution
"""

import os
import sys
import subprocess
import pty
import select
import fcntl
import time
import termios
import tty
import getpass
import json


def load_config():
    """Load configuration from config.json
    Returns: dict with config values, or empty dict if file not found"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.json')
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Warning: Could not load config.json: {e}")
            return {}
    return {}


def get_ssh_config():
    """Get SSH configuration from config.json
    Returns: (hostname, username, script_path) tuple or (None, None, None) if not configured"""
    config = load_config()
    imac_config = config.get('imac', {})
    
    if not imac_config.get('enabled', False):
        return None, None, None
    
    hostname = imac_config.get('hostname', '')
    username = imac_config.get('username', '')
    script_path = imac_config.get('script_path', '')
    
    if not hostname or not username or not script_path:
        return None, None, None
    
    return hostname, username, script_path


def run_ssh_with_password(ssh_cmd, password, timeout=600):
    """Run SSH command with password using pty (built-in Python module)
    Returns: (success: bool, exit_code: int)
    """
    # Create pseudo-terminal
    master_fd, slave_fd = pty.openpty()
    
    # Set terminal to raw mode for better password handling
    old_settings = termios.tcgetattr(master_fd)
    tty.setraw(master_fd)
    
    try:
        # Start SSH process
        process = subprocess.Popen(
            ssh_cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            preexec_fn=os.setsid,
            bufsize=0
        )
        
        # Close slave_fd in parent process
        os.close(slave_fd)
        
        # Set master_fd to non-blocking
        flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
        fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        
        buffer = b''
        password_sent = False
        start_time = time.time()
        last_activity = start_time
        max_wait_after_password = 10  # Max seconds to wait for response after sending password
        max_wait_for_prompt = 15  # Max seconds to wait for password prompt to appear
        fallback_password_timeout = 3  # If no prompt detected after this, try sending password anyway
        
        while True:
            # Check timeout
            elapsed = time.time() - start_time
            if timeout > 0 and elapsed > timeout:
                process.kill()
                return False, -1
            
            # Check if process is done
            if process.poll() is not None:
                # Read any remaining output
                try:
                    while True:
                        data = os.read(master_fd, 1024)
                        if not data:
                            break
                        buffer += data
                        # Print remaining output
                        decoded = buffer.decode('utf-8', errors='ignore')
                        # Don't print password prompts
                        if 'password:' not in decoded.lower() and 'Password:' not in decoded:
                            sys.stdout.write(decoded)
                            sys.stdout.flush()
                        buffer = b''
                except OSError:
                    pass
                break
            
            # Read from master_fd
            ready, _, _ = select.select([master_fd], [], [], 0.1)
            if ready:
                try:
                    data = os.read(master_fd, 1024)
                    if data:
                        buffer += data
                        last_activity = time.time()
                        decoded_output = buffer.decode('utf-8', errors='ignore')
                        
                        # Check for password prompt (more robust detection)
                        if not password_sent:
                            # Accumulate buffer and check for password prompts
                            # Don't clear buffer until we've sent password - prompts can come in chunks
                            lower_output = decoded_output.lower()
                            
                            # Very aggressive password prompt detection
                            # Check for ANY indication of password prompt, even partial
                            # Patterns to match:
                            # - "Password:" (anywhere)
                            # - "password:" (anywhere, lowercase)
                            # - "(anything) Password:" (keyboard-interactive)
                            # - ") Password:" (keyboard-interactive, partial)
                            # - "password for" (some SSH versions)
                            
                            # Ultra-simple and aggressive detection
                            # If we see "password" (case-insensitive) and ":" anywhere in output, send password
                            # This catches ALL variations: "Password:", "password:", "(user@host) Password:", etc.
                            has_password = 'password' in lower_output
                            has_colon = ':' in decoded_output
                            
                            # Also check elapsed time - if we've been waiting and see "password", try sending
                            elapsed_wait = time.time() - start_time
                            
                            # Send password if:
                            # 1. We see "password" and ":" (most common case)
                            # 2. We see "password" and have been waiting > 1 second (fallback for edge cases)
                            if (has_password and has_colon) or (has_password and elapsed_wait > 1.0):
                                # Found password prompt - send password immediately
                                os.write(master_fd, (password + '\n').encode('utf-8'))
                                password_sent = True
                                # Small delay to let SSH process the password
                                time.sleep(0.5)
                                # Clear buffer to avoid printing password prompt
                                buffer = b''
                                # Update last_activity since we just sent password
                                last_activity = time.time()
                        else:
                            # Print output in real-time (excluding password prompts)
                            if 'password:' not in decoded_output.lower() and 'Password:' not in decoded_output:
                                sys.stdout.write(decoded_output)
                                sys.stdout.flush()
                                buffer = b''
                except OSError as e:
                    if password_sent:
                        # If we've sent password and get OSError, process might be done
                        break
                    else:
                        raise
            else:
                # No data available
                if password_sent:
                    # After sending password, wait for response
                    elapsed_since_activity = time.time() - last_activity
                    if elapsed_since_activity > max_wait_after_password:
                        # Check if process is still running
                        if process.poll() is not None:
                            break
                else:
                    # If we haven't sent password yet, check if we should try fallback
                    elapsed_since_start = time.time() - start_time
                    
                    # Fallback: if we've been waiting a bit and process is still running,
                    # but haven't detected prompt, try sending password anyway
                    # This handles cases where prompt detection fails
                    if elapsed_since_start > fallback_password_timeout and elapsed_since_start < max_wait_for_prompt:
                        # Check if process is still running (waiting for input)
                        if process.poll() is None:
                            # Process is still alive, might be waiting for password
                            # Check if we have any output that suggests it's waiting
                            try:
                                # Try to peek at what's available
                                ready, _, _ = select.select([master_fd], [], [], 0)
                                if not ready:
                                    # No data available, process might be waiting for password
                                    # Try sending password as fallback
                                    os.write(master_fd, (password + '\n').encode('utf-8'))
                                    password_sent = True
                                    time.sleep(0.5)
                                    buffer = b''
                            except:
                                pass
                    
                    if elapsed_since_start > max_wait_for_prompt:
                        # Timeout waiting for password prompt
                        # Try to read any error output before giving up
                        try:
                            error_data = os.read(master_fd, 2048)
                            if error_data:
                                error_msg = error_data.decode('utf-8', errors='ignore')
                                # Don't return yet - let the process finish naturally
                                # But we'll know it timed out waiting for prompt
                                pass
                        except:
                            pass
                        # Continue waiting - the process might still be authenticating
        
        # Wait for process to finish
        exit_code = process.wait()
        return exit_code == 0, exit_code
        
    except Exception as e:
        try:
            process.kill()
        except:
            pass
        raise e
    finally:
        # Restore terminal settings
        try:
            termios.tcsetattr(master_fd, termios.TCSADRAIN, old_settings)
        except:
            pass
        os.close(master_fd)


def test_ssh_connection(hostname, username, password=None, timeout=10):
    """Test SSH connection to remote host
    Returns: (success: bool, error_message: str or None)
    """
    test_cmd = 'echo "SSH connection test successful"'
    
    try:
        if password:
            # Use password-based authentication
            ssh_cmd = [
                'ssh',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'ConnectTimeout=10',
                f'{username}@{hostname}',
                test_cmd
            ]
            success, exit_code = run_ssh_with_password(ssh_cmd, password, timeout=timeout)
            if success:
                return True, None
            else:
                # Exit code 255 from SSH typically means:
                # - Authentication failure (wrong password)
                # - Connection refused (SSH service not running)
                # - Host unreachable (network issue)
                # - Permission denied
                if exit_code == 255:
                    return False, f"SSH connection test failed (exit code 255). This usually means: wrong password, authentication failed, connection refused, or host unreachable. Try running 'ssh {username}@{hostname}' manually to verify credentials and network connectivity."
                else:
                    return False, f"SSH connection test failed with exit code {exit_code}. Common causes: wrong password, host unreachable, or SSH service not running."
        else:
            # Try without password (assumes SSH keys are set up)
            ssh_cmd = [
                'ssh',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'ConnectTimeout=10',
                '-o', 'BatchMode=yes',  # Fail if password is required but not provided
                f'{username}@{hostname}',
                test_cmd
            ]
            result = subprocess.run(
                ssh_cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return True, None
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                return False, f"SSH connection test failed: {error_msg}"
                
    except subprocess.TimeoutExpired:
        return False, "SSH connection test timed out (host may be unreachable)"
    except FileNotFoundError:
        return False, "SSH command not found. Is SSH installed?"
    except Exception as e:
        return False, f"Error testing SSH connection: {str(e)}"


def prompt_for_ssh_password():
    """Prompt user for SSH password securely
    Returns: password string or None if cancelled"""
    try:
        password = getpass.getpass("Enter SSH password: ")
        return password if password else None
    except KeyboardInterrupt:
        print("\n❌ Password entry cancelled")
        return None
    except Exception as e:
        print(f"\n❌ Error reading password: {e}")
        return None


def execute_remote_command(hostname, username, remote_cmd, password=None, timeout=600):
    """Execute a command on remote host via SSH
    Returns: (success: bool, exit_code: int, error_message: str or None)
    """
    ssh_cmd = [
        'ssh',
        '-o', 'StrictHostKeyChecking=no',
        f'{username}@{hostname}',
        remote_cmd
    ]
    
    try:
        if password:
            success, exit_code = run_ssh_with_password(ssh_cmd, password, timeout=timeout)
            if success:
                return True, exit_code, None
            else:
                return False, exit_code, f"Remote command failed with exit code {exit_code}"
        else:
            # No password provided, use regular SSH (will prompt interactively or use SSH keys)
            result = subprocess.run(
                ssh_cmd,
                check=False,
                capture_output=False,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return True, result.returncode, None
            else:
                return False, result.returncode, f"Remote command failed with exit code {result.returncode}"
                
    except subprocess.TimeoutExpired:
        return False, -1, "SSH command timed out (remote machine may be unreachable)"
    except FileNotFoundError:
        return False, -1, "Error: SSH command not found. Is SSH installed?"
    except Exception as e:
        return False, -1, f"Error running SSH command: {e}"


def verify_ssh_setup():
    """Verify SSH is configured and prompt for password if needed
    Returns: (success: bool, password: str or None, error_message: str or None)
    """
    hostname, username, script_path = get_ssh_config()
    
    if not hostname or not username or not script_path:
        return False, None, "SSH configuration incomplete. Please check config.json"
    
    # Check if password is already in environment
    ssh_password = os.environ.get('SSH_PASSWORD', '')
    
    # If no password in environment, prompt for it
    if not ssh_password:
        print(f"\n📡 SSH Mode: Connecting to {username}@{hostname}")
        ssh_password = prompt_for_ssh_password()
        if not ssh_password:
            return False, None, "Password entry cancelled or failed"
    
    # Test the connection
    print(f"\n🔍 Testing SSH connection to {hostname}...")
    success, error = test_ssh_connection(hostname, username, ssh_password, timeout=15)
    
    if success:
        print("✅ SSH connection verified!")
        return True, ssh_password, None
    else:
        return False, None, error

