# Execute

To fetch all the latest data and plot the bubbles:

```
python update_and_check_bubbles.py
```


# Development 

Format the code:
```
python setup.py format
```

To debug, check the configurations in `launch.json` and the files under '/lppls/demo'


# See daily bubbles

I run this daily on the mac using the files under `mac_automation".

I place the launch agent under '~/Library/LaunchAgents', then run:

```
launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.octaviantuchila.daily_sornette.plist
```

# Other notes 

The Jupyter code and `lppls_cmaes` are from the repository I've forked.
They don't work.
TODO(octaviant) - update or more likely, remove


Testing - not functional; TODO(octaviant) - fix existing testing and add new tests.