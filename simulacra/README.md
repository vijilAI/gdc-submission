# Simulacra of Red Teamers

First cut to stand up the [Simulacra](https://docs.google.com/document/d/1Z-Z7fA8PftuUrwedNIuzL3Tg6bT6XshszdORvYOcj90/edit?usp=drive_link).

## Structure
```
configs # agent system prompt (templates)
personas # persona variables
types.py # basic data types
agent_v2.py # currently used classes
agent_v2.py # old deprecated classes
chat.py # code for chat UI
dashboard.py # code for dashboard UI
```

## Instructions

### Python
1. Store a together API key in a `.env` file in `poc_projects` root.
2. Install packages from `requirements.txt`.
3. Run red teaming conversations and sessions inside the `scratchpad.ipynb`.

You can change Hub/LLMs used in the SUT/Redbots by going inside `configs/*.yaml`. If you do so make sure to have respective hub API keys in your env.

### UI
To run Chat/dashboard UIs locally, use `streamlit run filename.py` from bash.

A bunch of sessions are available [here](https://drive.google.com/file/d/1cfJHrpeudQ32mFcL_dg_xpxfuCZ5FSER/view?usp=drive_link) that can be visualized in the dashboard.

