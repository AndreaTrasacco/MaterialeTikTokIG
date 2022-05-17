from crontab import CronTab

'''
    pip install python-crontab
'''

user = "atrasacco"
command = " python3 /home/" + user + "/TikTokIG/tiktok_ig.py >> /home/" + user + "/TikTokIG/output.txt 2>&1"


# It works for Linux systems
cron = CronTab(user=user)
job = cron.new(command=command)
job.setall('0 1 * * *') # Every day at 01:00
cron.write()