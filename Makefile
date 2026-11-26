PY ?= python

.PHONY: setup smoke validate radio film narration keyframes shots music assemble wan-jobs music-jobs clean-final

setup:            ## install dependencies
	$(PY) -m pip install -r requirements.txt

smoke:            ## call each provider once, log latency
	$(PY) pipeline/smoke_test.py

validate:         ## validate storyboard.json against the schema
	$(PY) -c "import sys; sys.path.insert(0,'pipeline'); from common import load_storyboard; load_storyboard(); print('storyboard OK')"

radio:            ## radio cut: narration + music on black
	$(PY) pipeline/run.py --radio

film:             ## the whole pipeline, cached
	$(PY) pipeline/run.py

narration keyframes shots assemble:
	$(PY) pipeline/$@.py $(ARGS)

music:
	$(PY) pipeline/music.py --duration 120

wan-jobs:         ## export Wan jobs for Kaggle
	$(PY) pipeline/shots.py --export-jobs

music-jobs:       ## export ACE-Step jobs for Kaggle
	$(PY) pipeline/music.py --export-jobs
