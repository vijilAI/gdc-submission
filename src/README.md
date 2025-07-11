# This portion of the repo contains code as part of a submission to the global dialogue challenges. 

Our approach was to examine how different demographic features and views about AI can be used to more broadly test 
behaviors and functionality of various LLM. To do this we constructed a pipeline that injest survye responses 
from the Global Dialogue Survey and uses them to form personas. These personas are then combined with a 
agent specificiation (namely system prompt) to generate a persona specific goal. This goal can be
either good faith or bad faith. These goals are then used to initiate a back and forrth simulated 
chat session with the agent and the persona. 


The GD1_gatheyr.ipynb shows a minimal set of commands to run to A) generate the persona jsons and B) run a session between a persona and an agent. 

The GD1_participants.csv, which can an be found https://github.com/collect-intel/global-dialogues,  is used to generate the personas). 
A preformatted set of jsons to use for this application can be found https://drive.google.com/drive/folders/1BP1PRPlY5AFA7w2Zynduzz_8qHic2flu?usp=drive_link. These personas can be placed in the personas/ directory and populate_db.py can be run to get it into the database.


