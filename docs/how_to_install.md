# How to Install

## What you need before starting

- Internet connection
- macOS

---

## Steps

1. Download **`install.command`** from the repo
2. Right-click it → click **Open** (you must right-click the first time — double-clicking will be blocked by Gatekeeper)
3. A Terminal window will open — follow the prompts
4. When asked, type the **number** next to your drive and press Enter
5. Choose where to install:
   - Press **Enter** to install at the drive root
   - Type a **folder name** (e.g. `py`) to install inside that folder on the drive
   - Type a **full path** starting with `/` to install anywhere on the Mac
6. `config.json` will open in TextEdit at the end — fill in your values, then save and close

That's it. You're done.

---

## After installing

- **To pull updates:** double-click `git_pull.command` in the repo folder
- **To run the download workflow:** double-click `download/Run Trigger Download.command`
- **To create playlists:** double-click `library/Create Playlists.command`

---

## If something goes wrong

| What you see | What to do |
|---|---|
| "cannot be opened because it is from an unidentified developer" | Right-click the file → Open |
| "Git is not installed" | The installer will handle this — follow the Y/N prompts |
| "Python 3 is not installed" | Download from https://www.python.org/downloads/ and re-run |
| Clone failed | Check your internet connection and try again |
| Any other error | Screenshot the terminal window and ask for help |
