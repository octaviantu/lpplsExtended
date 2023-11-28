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
launchctl unload  ~/Library/LaunchAgents/com.octaviantuchila.daily_sornette.plist # if already loaded
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.octaviantuchila.daily_sornette.plist
```

DO NOT put the codebase under `Documents`, because the mac launcher won't be allowed to access it.
