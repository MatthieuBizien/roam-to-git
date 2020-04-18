# Automatic RoamResearch backup

This script help you backup your [RoamResearch](https://roamresearch.com/)!

This script automatically
- Download a markdown archive of your RoamResearch workspace
- Download a json archive of your RoamResearch workspace
- Unzip them to your git directory
- Commit and push the difference

# Why to use it

- You have a backup if RoamResearch lose some of your data.
- You have a history of your notes.
- You can browse your Github repository with a mobile phone.

# How to use it

## Setup

### Install Roam-To-Git
With [pipx](https://github.com/pipxproject/pipx) 
(if you don't know pipx, you should look at it, it's wonderful!)

`pipx install git+https://github.com/MatthieuBizien/roam-to-git.git`

### Create a (private) Github repository for all your notes

With [gh](https://github.com/cli/cli): `gh repo create notes` (yes, it's private)

Or [manually](https://help.github.com/en/github/getting-started-with-github/create-a-repo)

Then run `git push --set-upstream origin master`

### Configure environment variables

- `curl https://raw.githubusercontent.com/MatthieuBizien/roam-to-git/master/env.template > notes/.env`
- Fill the .env file: `vi .env`
- Ignore it: `echo .env > notes/.gitignore; cd notes; git add .gitignore; git commit -m "Initial commit"`

## Manual backup

- Run the script: `roam-to-git notes/`
- Check your Github repository, it should be filled with your notes :)

## Automatic backup

One-liner to run it with a [cron](https://en.wikipedia.org/wiki/Cron) every hours: 
`echo "0 *  *  *  *  '$(which roam-to-git)' '$(pwd)/notes'" | crontab -`

# Task list

## Backup all RoamResearch data

- [x] Download automatically from RoamResearch
- [x] Create Cron
- [x] Write detailed README
- [x] Publish the repository on Github
- [ ] Download images (they currently visible in Github, but not in the archive so not saved in the repository 😕)

## Format the backup to have a good UI

### Link formatting to be compatible with Github markdown
- [x] Format `[[links]]`
- [x] Format `#links`
- [x] Format `attribute::`
- [ ] Format `[[ [[link 1]] [[link 2]] ]]` 
- [ ] Format `((link))`

### Backlink formatting
- [x] Add backlinks reference to the notes files
- [x] Integrate the context into the backlink
- [ ] Manage `/` in file names

### Other formatting
- [x] Format `{{TODO}}` to be compatible with Github markdown
- [ ] Format `{{query}}``

## Make it for others
- [x] Push it to Github
- [ ] Add example repository
- [x] Make the backup directory configurable
- [ ] Publicize it
    - [ ] [RoamResearch Slack](https://roamresearch.slack.com/)
    - [ ] [RoamResearch Reddit](https://www.reddit.com/r/RoamResearch/)
    - [ ] Twitter

## Add features
- [ ] Add automatic Google Keep retrieval

## Some ideas, I don't need it, but PR welcome 😀
- [ ] Test it/make it work on Windows
- [ ] Pre-configure a CI server so it can run every hour without a computer
