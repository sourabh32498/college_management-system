# Student Management (Django + Bootstrap)

## 1) Open Project Folder

```powershell
cd "C:\Users\swapn\Desktop\student management\student"
```

## 2) Create Virtual Environment (first time only)

```powershell
python -m venv venv
```

## 3) Activate Virtual Environment

```powershell
.\venv\Scripts\Activate.ps1
```

## 4) Install Dependencies

```powershell
pip install -r requirements.txt
```

If `requirements.txt` is empty, install Django directly:

```powershell
pip install django
```

## 5) Apply Migrations

```powershell
python manage.py migrate
```

## 6) Create Superuser

```powershell
python manage.py createsuperuser
```

## 7) Run Development Server

```powershell
python manage.py runserver
```

Open: `http://127.0.0.1:8000/`

## 8) Useful Commands

```powershell
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput
```

## Project Notes

- Django project module: `student`
- Main app: `Students`
- Bootstrap 5 loaded from CDN in base template
- Custom styles: `Students/static/Students/css/site.css`
