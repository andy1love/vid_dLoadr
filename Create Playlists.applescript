-- Create Playlists AppleScript Applet
-- To create an app: Open this file in Script Editor, then File > Export > Format: Application

on run
	set scriptPath to path to me as string
	set scriptFolder to (characters 1 thru -5 of scriptPath) as string
	set scriptDir to POSIX path of scriptFolder
	set pythonScript to scriptDir & "create_playlist.py"
	
	try
		set resultText to do shell script "cd " & quoted form of scriptDir & " && python3 create_playlist.py"
		display dialog "Playlist creation completed!" & return & return & resultText buttons {"OK"} default button "OK" with icon note giving up after 10
	on error errMsg
		display dialog "Error running script:" & return & return & errMsg buttons {"OK"} default button "OK" with icon stop
	end try
end run

