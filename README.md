# Automatic RoamResearch backup

[![Roam Research backup](https://github.com/MatthieuBizien/roam-to-git-demo/workflows/Roam%20Research%20backup/badge.svg)](https://github.com/MatthieuBizien/roam-to-git-demo/actions)
[![roam-to-git tests.py](https://github.com/MatthieuBizien/roam-to-git/workflows/roam-to-git%20tests.py/badge.svg)](https://github.com/MatthieuBizien/roam-to-git/actions)

This script helps you backup your [RoamResearch](https://roamresearch.com/) graphs!

This script automatically
- Downloads a markdown archive of your RoamResearch workspace
- Downloads a json archive of your RoamResearch workspace
- Unzips them to your git directory
- Commits and pushes the difference to Github

# Demo
[See it in action!](https://github.com/MatthieuBizien/roam-to-git-demo). This repo is updated using roam-to-git.

# Why to use it

- You have a backup if RoamResearch loses some of your data.
- You have a history of your notes.
- You can browse your Github repository easily with a mobile device


# Use it with Github Actions (recommended)

**Note**: [Erik Newhard's guide](https://eriknewhard.com/blog/backup-roam-in-github) shows an easy way of setting up Github Actions without using the CLI.

##  Create a (private) Github repository for all your notes

With [gh](https://github.com/cli/cli): `gh repo create notes` (yes, it's private)

Or [manually](https://help.github.com/en/github/getting-started-with-github/create-a-repo)

## Configure Github secrets 

- Go to github.com/your/repository/settings/secrets 

###

Add 3 (separate) secrets where the names are 

`ROAMRESEARCH_USER`

`ROAMRESEARCH_PASSWORD`

`ROAMRESEARCH_DATABASE`

- Refer to [env.template](env.template) for more information

- when inserting the information, there is no need for quotations or assignments

![image](https://user-images.githubusercontent.com/173090/90904133-2cf1c900-e3cf-11ea-960d-71d0543b8158.png)


## Add GitHub action

```
cd notes
mkdir -p .github/workflows/
curl https://raw.githubusercontent.com/MatthieuBizien/roam-to-git-demo/master/.github/workflows/main.yml > \
    .github/workflows/main.yml
git add .github/workflows/main.yml
git commit -m "Add github/workflows/main.yml"
git push --set-upstream origin master
```

## Check that the Github Action works

- Go to github.com/your/repository/actions
- Your CI job should start in a few seconds

### Note:

If the backup does not automatically start, try pushing to the repository again


# Use it locally

**Note**: if your file system is not case-sensitive, you will not backup notes that have the same name in different 
cases

## Install Roam-To-Git
With [pipx](https://github.com/pipxproject/pipx) 
(if you don't know pipx, you should look at it, it's wonderful!)

`pipx install git+https://github.com/MatthieuBizien/roam-to-git.git`

## Create a (private) Github repository for all your notes

With [gh](https://github.com/cli/cli): `gh repo create notes` (yes, it's private)

Or [manually](https://help.github.com/en/github/getting-started-with-github/create-a-repo)

Then run `git push --set-upstream origin master`

## Configure environment variables

- `curl https://raw.githubusercontent.com/MatthieuBizien/roam-to-git/master/env.template > notes/.env`
- Fill the .env file: `vi .env`
- Ignore it: `echo .env > notes/.gitignore; cd notes; git add .gitignore; git commit -m "Initial commit"`

## Manual backup

- Run the script: `roam-to-git notes/`
- Check your Github repository, it should be filled with your notes :)

## Automatic backup

One-liner to run it with a [cron](https://en.wikipedia.org/wiki/Cron) every hours: 
`echo "0 *  *  *  *  '$(which roam-to-git)' '$(pwd)/notes'" | crontab -`

NB: there are [issues](https://github.com/MatthieuBizien/roam-to-git/issues/43) on Mac with a crontab.

# Debug

Making `roam-to-git` foolproof is hard, as it depends on Roam, on Github Action or the local environment, 
on software not very stable (`pyppeteer` we still love you 😉 )
and on the correct user configuration.

For debugging, please try the following:

- Check that the environment variables `ROAMRESEARCH_USER`, `ROAMRESEARCH_PASSWORD`, `ROAMRESEARCH_DATABASE` are correctly setup
- Login into Roam using the username and the password. 
You may want to ask a new password if you have enabled Google Login, as it solved some user problems.
- Run `roam-to-git --debug` to check the authentification and download work
- Look at the traceback
- Look for similar issues
- If nothing else work, create a new issue with as many details as possible. 
I will try my best to understand and help you, no SLA promised 😇

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
- [x] Manage `/` in file names

### Other formatting
- [x] Format `{{TODO}}` to be compatible with Github markdown
- [ ] Format `{{query}}``

## Make it for others
- [x] Push it to Github
- [x] Add example repository
- [x] Make the backup directory configurable
- [ ] Publicize it
    - [x] [RoamResearch Slack](https://roamresearch.slack.com/) [thread](https://roamresearch.slack.com/archives/CN5MK4D2M/p1588670473431200)
    - [ ] [RoamResearch Reddit](https://www.reddit.com/r/RoamResearch/)
    - [ ] Twitter

## Some ideas, I don't need it, but PR welcome 😀
- [ ] Test it/make it work on Windows
- [x] Pre-configure a CI server so it can run every hour without a computer
    Thanks @Stvad for [#4](https://github.com/MatthieuBizien/roam-to-git/issues/4)!
