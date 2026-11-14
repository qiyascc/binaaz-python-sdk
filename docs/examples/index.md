# Examples

Complete scripts you can copy, run and change. Each one is a single file that uses only the SDK and the standard library, unless it says otherwise.

| Example | What it shows |
| --- | --- |
| [A session file](session-file.md) | Sign in once by email or SMS, save the cookie, reuse it, sign in again when it expires |
| [Post from a folder](post-from-folder.md) | One folder per flat with a `listing.json` and the photos, posted in one go |
| [Export to CSV](export-csv.md) | Every listing of the account with its state, price and expiry date in a spreadsheet |
| [A daily prolong job](prolong-job.md) | Prolong listings that expire soon, run from cron or Windows Task Scheduler |
| [Alert on rejected listings](rejected-alert.md) | Check the rejected tab and send a Telegram message for new rejections |
| [Django](django.md) | A Django model for listings, a management command that posts them, and the session kept in the database |

The repository has two more small scripts in [examples/](https://github.com/qiyascc/binaaz-python-sdk/tree/main/examples).
