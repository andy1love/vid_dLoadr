#!/bin/bash
# =============================================================================
#  video_curator_downloader installer — macOS
#  Download this file, right-click → Open, follow the prompts.
# =============================================================================

REPO_URL="https://github.com/andy1love/vid_dLoadr.git"
FOLDER_NAME="video_curator_downloader"

echo ""
echo "================================================="
echo "  video_curator_downloader  —  Setup"
echo "================================================="
echo ""

# --------------------------------------------------------------------------
# 1. Check for git; offer to install if missing
# --------------------------------------------------------------------------
check_git() {
    command -v git &>/dev/null
}

if ! check_git; then
    echo "Git is not installed on this Mac."
    echo ""
    while true; do
        read -rp "Install it now? (Y/N): " ans
        case "$ans" in
            [Yy])
                echo ""
                echo "Opening the macOS developer tools installer..."
                echo "A popup window will appear. Click 'Install' and wait for it to finish."
                echo ""
                xcode-select --install 2>/dev/null
                echo ""
                read -rp "Press Y when the installation is complete, or N to abort: " done_ans
                case "$done_ans" in
                    [Yy]) ;;
                    *) echo "Aborted."; read -n 1; exit 1 ;;
                esac
                if ! check_git; then
                    echo ""
                    echo "Git still not detected. Please make sure the installation"
                    echo "completed fully, then run this script again."
                    read -n 1
                    exit 1
                fi
                echo "Git installed successfully."
                break
                ;;
            [Nn])
                echo "Git is required. Aborting."
                read -n 1
                exit 1
                ;;
            *)
                echo "Please enter Y or N."
                ;;
        esac
    done
fi

echo "Git found: $(git --version)"
echo ""

# --------------------------------------------------------------------------
# 2. Check for Python 3
# --------------------------------------------------------------------------
if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python 3 is not installed."
    echo "Download it from https://www.python.org/downloads/ and re-run this installer."
    read -n 1
    exit 1
fi

echo "Python found: $(python3 --version)"
echo ""

# --------------------------------------------------------------------------
# 3. Detect drives (internal + external)
# --------------------------------------------------------------------------
SYSTEM_VOLUMES=("Preboot" "Recovery" "VM" "Data" "Update")

get_drives() {
    for vol in /Volumes/*/; do
        name=$(basename "$vol")
        skip=false
        for sv in "${SYSTEM_VOLUMES[@]}"; do
            [[ "$name" == "$sv" ]] && skip=true && break
        done
        [[ "$name" == com.apple.* ]] && skip=true
        [[ "$skip" == false ]] && printf '%s\n' "$name"
    done
}

DRIVES=()
while IFS= read -r line; do
    DRIVES+=("$line")
done < <(get_drives)

if [ ${#DRIVES[@]} -eq 0 ]; then
    echo "No drives detected under /Volumes/."
    read -n 1
    exit 1
fi

echo "Available drives:"
echo ""
for i in "${!DRIVES[@]}"; do
    echo "  [$((i+1))] ${DRIVES[$i]}"
done
echo ""

CHOSEN_DRIVE=""
while true; do
    read -rp "Enter the number of the drive to install onto: " choice
    if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#DRIVES[@]}" ]; then
        CHOSEN_DRIVE="${DRIVES[$((choice-1))]}"
        break
    fi
    echo "Invalid choice. Enter a number between 1 and ${#DRIVES[@]}."
done

echo ""
echo "Where on this drive should the scripts be installed?"
echo "  Options:"
echo "    Press Enter      → /Volumes/$CHOSEN_DRIVE/$FOLDER_NAME"
echo "    Type a name      → /Volumes/$CHOSEN_DRIVE/NAME/$FOLDER_NAME   (e.g. py)"
echo "    Type a full path → /your/custom/path/$FOLDER_NAME             (must start with /)"
echo ""
read -rp "Subfolder name, full path, or Enter to skip: " SUBFOLDER
SUBFOLDER=$(echo "$SUBFOLDER" | sed 's/[[:space:]]*$//')

if [[ "$SUBFOLDER" == /* ]]; then
    INSTALL_ROOT="${SUBFOLDER%/}"
elif [ -n "$SUBFOLDER" ]; then
    SUBFOLDER=$(echo "$SUBFOLDER" | tr -d '/')
    INSTALL_ROOT="/Volumes/$CHOSEN_DRIVE/$SUBFOLDER"
else
    INSTALL_ROOT="/Volumes/$CHOSEN_DRIVE"
fi
INSTALL_PATH="$INSTALL_ROOT/$FOLDER_NAME"

echo ""
echo "Install to: $INSTALL_PATH"
echo ""
while true; do
    read -rp "Confirm? (Y/N): " confirm
    case "$confirm" in
        [Yy]) break ;;
        [Nn]) echo "Aborted."; read -n 1; exit 0 ;;
        *) echo "Please enter Y or N." ;;
    esac
done

# --------------------------------------------------------------------------
# 4. Clone repo
# --------------------------------------------------------------------------
echo ""
if [ -d "$INSTALL_PATH/.git" ]; then
    echo "Repo already exists at $INSTALL_PATH — skipping clone."
else
    echo "Cloning repo..."
    git clone "$REPO_URL" "$INSTALL_PATH"
    if [ $? -ne 0 ]; then
        echo ""
        echo "ERROR: Clone failed. Check your internet connection and try again."
        read -n 1
        exit 1
    fi
fi

# --------------------------------------------------------------------------
# 5. Install Python dependencies
# --------------------------------------------------------------------------
echo ""
echo "Installing Python dependencies..."
pip3 install -r "$INSTALL_PATH/requirements.txt"
if [ $? -ne 0 ]; then
    echo ""
    echo "WARNING: pip3 install encountered errors. Some features may not work."
    echo "You can retry later with: pip3 install -r $INSTALL_PATH/requirements.txt"
fi

# --------------------------------------------------------------------------
# 6. Create config.json
# --------------------------------------------------------------------------
TEMPLATE="$INSTALL_PATH/config.json.example"
CONFIG="$INSTALL_PATH/config.json"

if [ -f "$CONFIG" ]; then
    echo ""
    echo "config.json already exists — skipping."
else
    cp "$TEMPLATE" "$CONFIG"
    echo ""
    echo "config.json created from config.json.example."
fi

# --------------------------------------------------------------------------
# 7. Open config.json for final review
# --------------------------------------------------------------------------
echo ""
echo "-------------------------------------------------"
echo "  Almost done!"
echo ""
echo "  config.json will open in TextEdit."
echo "  Fill in the following values for your setup:"
echo ""
echo "    download_dir_mp4  — where MP4 files are saved"
echo "    download_dir_mp3  — where MP3 files are saved"
echo "    crate_output_dir  — Serato subcrates folder"
echo "    imac.hostname     — your iMac's local IP address"
echo "    imac.username     — your iMac username"
echo "    imac.script_path  — path to scripts folder on iMac"
echo ""
echo "  Save and close when done."
echo "-------------------------------------------------"
echo ""
read -rp "Press Enter to open config.json..."
open -a TextEdit "$CONFIG"

echo ""
echo "================================================="
echo "  Setup complete!"
echo "  Scripts are in: $INSTALL_PATH"
echo "  For future updates, double-click git_pull.command"
echo "================================================="
echo ""
echo "Done. Press any key to close."
read -n 1
