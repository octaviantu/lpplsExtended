# Execute

To fetch all the latest data and plot the bubbles:

```
python update_and_check_bubbles.py
```


# Development 

Install dependencies:
```
python setup.py install -e .
```

Format the code:
```
python setup.py format
```

To debug the fit parameters, check the configurations in `launch.json` and the files under '/lppls/demo'


# See daily bubbles

I run this daily on the mac using the files under `mac_automation".

I place the launch agent under '~/Library/LaunchAgents', then run:

```
launchctl unload  ~/Library/LaunchAgents/com.octaviantuchila.daily_sornette.plist # if already loaded
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.octaviantuchila.daily_sornette.plist
```

DO NOT put the codebase under `Documents`, because the mac launcher won't be allowed to access it.

# Run on a Linux VM
With docker compose

```
sudo docker-compose up -d
sudo docker-compose logs -f app
```

As a single docker container, which connects to the local DB
```
docker run --network="host" lppls
nohup sudo docker run --network="host" lppls &
```
To see the logs:
```
tail -f nohup.out
```

# Deploy to Google Cloud - Artifact Registry

docker build --platform linux/amd64 -t europe-west2-docker.pkg.dev/sornette/lppls-reg/lppls:amd-64 .
docker push europe-west2-docker.pkg.dev/sornette/lppls-reg/lppls:amd-64

# Other spefications

1. The code always does not take into account today's price.
That's because I want consistency: I usually run it before market open.
If I run other historic simulations, they should also be before market open.

2. As a consequence of 1, I don't run the code on Sundays and Mondays.
