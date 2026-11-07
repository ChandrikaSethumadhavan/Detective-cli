# Prompts as typed

Selected prompts that shaped this project, quoted exactly as I typed them, typos included. Short approval messages such as "I reviewed it, approve T-5" and pasted terminal output are left out. What each prompt produced is in [ai-log.md](ai-log.md).

## 1. Plan and architecture

> I need to first make a plan and plan the architecture to build the idea mentioned in info/pdf, create a detail html doducment mentioning the architecture you'll use (maybe for storage think of redis or tigercloud if needed) as well create a detailed flow diagram of the architecture and the flow of events, for aAI agents i would use google ai studio's free models or openrouter models. I'm making it for a company's case study

## 2. Standing instructions for the whole build

> Refer to docs/*.html for the detailed plan about what to build in this repo. Do not push or commot changes to GitHub without asking me. Do not write excessive comments, route to smaller models for smaller tasks and use opus or expensive models only when the task is critical

## 3. Feedback after trying the Docker image

> okay some feedback from me 1. When importing the cli, first print message should be regarding privacy of the repo that it is being instaleld to 2.A company trying this tool wont try this on their own repo, so should i create a dummy test case somehow? like a test repo or something easier??? 3.There should be more print outputs regarding the status of the repo because [image of the case study brief], since it says list of findings with line as well as short reason for each, combine this with the dummy test i mentioned

## 4. Making it easy for other people to run

> if somebody else wnats to use it, how will it work? should i dockerise it? what do u sugegst

> like what if someone who does not even have python installed in the system runs it?

> so how will someone else run it since you are saying it must be run inside my own repo

## 5. Scanning commits, not only uncommitted changes

> but why is notthing printed on the command line then? about the PR things? i want to see something likr no secrets fpound in the commits of this repo, or xyz found in the commits of this repo

## 6. The interactive menu

> okay i've tried everything, my quetsion is, now that you know its the ai-work directory im trying on so it works easily, byt for the recruiter we dont know what repo or folder he's gonna try it on right? so shouldnt it be easier? i feel like these are way too many steps, so when the image is built and then run, there should be 2 options popping up, 1. try demo 2.try it on your own folder and under this option 2 when selected, it should ask for the folder to try it on and then show 1.json 2.range of all commits 3.exit, when selected it shoud show the result and then go back to selecting 1 or 2 (json or range ) and 3.try demo 4.exit.. when demo is tried, it must land on these optiopns back again. all on command line. make these chnages, then tell me to commit and push and then try the steps. It must be really user friendly

## 7. Checking the result against the brief

> so is my project satiofying all of their requirements?
