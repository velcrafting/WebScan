from apscheduler.schedulers.blocking import BlockingScheduler
import subprocess


def run_command(cmd):
    subprocess.run(cmd, shell=True, check=False)


def schedule_jobs():
    scheduler = BlockingScheduler()
    scheduler.add_job(lambda: run_command('python main.py geo:serp-reddit --queries data/queries.json --top 5'), 'cron', hour='9,21', minute=0)
    scheduler.add_job(lambda: run_command('python main.py geo:llm-probe --queries data/queries.json'), 'cron', hour='9,21', minute=5)
    scheduler.add_job(lambda: run_command('python main.py geo:index-check'), 'cron', minute='*/180')
    scheduler.add_job(lambda: run_command('python main.py eng:brand-activity --users data/brand_accounts.json --lookback 60'), 'cron', minute=15, hour='*/6')
    scheduler.add_job(lambda: run_command('python main.py eng:fud-scan --subreddits data/subreddits.json --lookback 14 --limit 400'), 'cron', minute=30, hour='*/6')
    scheduler.start()