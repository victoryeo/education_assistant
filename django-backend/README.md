## setup the python venv
python3 -m venv .venv 

## activate the venv
source .venv/bin/activate

## install the required packages
pip install -r requirements.txt

## run the django app
python manage.py runserver