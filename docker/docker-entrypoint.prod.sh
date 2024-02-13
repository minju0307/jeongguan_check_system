#!/bin/bash
service ssh start

#jupyter lab \
#        --ip 0.0.0.0                               `# Run on localhost` \
#        --allow-root                               `# Enable the use of sudo commands in the notebook` \
#        --no-browser                               `# Do not launch a browser by default` \
#        --NotebookApp.token="$JUPYTER_TOKEN"       `# Do not require token to access notebook` \
#        --NotebookApp.password=""

export PYTHONPATH=.
python tasks/xai_llm_law.py > task_1.log 2>&1 &
python web_server.py
tail -f /dev/null
