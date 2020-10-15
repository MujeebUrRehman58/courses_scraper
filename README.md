### Instructions to run this project:

1.  Set these env vars (MAIL, PASSWORD, LOGIN_API, IMAGE_API, COURSE_API).
2.  Create a python virtual environment (optional but recommended).
3.  Open terminal and activate virtual env.
4.  Change your working directory to project root folder. 
5.  Run "pip install -r requirements.txt" command to install all of the required libraries.
6.  Download chromedriver (driver version should match your chrome browser version).
7.  Copy and paste driver file in /courses/courses/spiders/chromedriver/ folder.
8.  Replace existing urls and categories data in /courses/courses/spiders/urls.csv with your desired urls and categories.
9.  Open main.py file and replace 'json/scraped_data.json' with your json data file path
10. CD to /courses and Run 'python main.py' to scrape data.
11. After data is successfully scraped run 'python upload_data.py /full-path/to/your/json/data/file' to create courses.

And you are done. 