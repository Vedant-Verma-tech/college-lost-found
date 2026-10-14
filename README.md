# ✦ CampusFind — College Lost & Found Portal

CampusFind is a web-based lost-and-found management system designed for college campuses. It helps students report lost belongings, submit found-item reports, and claim their missing possessions through a structured verification process.

The platform provides role-based access for students, teachers, and administrators, along with email OTP verification, claim management, notifications, and handover verification.

## 🚀 Features

### 👤 User Authentication
- Student registration with email OTP verification.
- Username and password login.
- Custom user roles: Student, Teacher, and Admin.
- Secure password handling through Django authentication.
- Email verification codes with expiry and usage restrictions.

### 🔎 Lost & Found Reports
- Submit lost-item and found-item reports.
- Add item descriptions, categories, locations, dates, and images.
- Browse available lost and found reports.
- Track submitted reports and their status.

### 📦 Claim Management
- Submit claims for found items with identifying details.
- Review and approve or reject claims.
- Track claim status through the user dashboard.
- Verify item handovers using a separate verification code.

### 🔔 Notifications
- Receive notifications about relevant report and claim activity.
- Track notification read status.

### 🛡️ Role-Based Dashboards
- **Students:** Manage reports and track claims.
- **Teachers:** Review submitted reports and manage claim requests.
- **Administrators:** Manage reports, users, roles, and platform activity.

### ☁️ Deployment and Storage
- PostgreSQL database support through Neon.
- Cloudinary integration for image storage.
- Environment-based configuration for secrets and email credentials.
- Deployment configured for Vercel.

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Django | Web framework |
| HTML5 | Page structure |
| CSS3 | Styling and responsive layouts |
| JavaScript | Frontend interactions |
| PostgreSQL | Production database |
| SQLite | Optional local development database |
| Neon | Managed PostgreSQL hosting |
| Cloudinary | Image storage |
| Gmail SMTP | OTP email delivery |
| Vercel | Deployment |
| Git and GitHub | Version control |

## 📂 Project Structure

```text
college-lost-found/
│
├── accounts/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── ...
│
├── reports/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── ...
│
├── dashboard/
│   └── ...
│
├── templates/
│   ├── accounts/
│   ├── reports/
│   └── base.html
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
├── manage.py
├── requirements.txt
├── .gitignore
├── .env.example
└── README.md
```

*The structure above is illustrative. Your actual project may contain additional files and folders.*

## ⚙️ Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/Vedant-Verma-tech/college-lost-found.git
cd college-lost-found
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

If you use Command Prompt instead:

```bat
venv\Scripts\activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root, alongside `manage.py`.

Example:

```dotenv
SECRET_KEY=replace-with-your-django-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Use your local database or your configured PostgreSQL URL.
DATABASE_URL=replace-with-your-database-url

# Email configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com

# Add the Cloudinary variables required by your settings.py.
```

**Important:** These are example variable names. Use the exact names read by your project's `settings.py`. Never commit real credentials or your production database URL to GitHub. Keep `.env` in `.gitignore`.

### 5. Apply database migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

If your project already has migration files, keep them. For production, run migrations against the intended production database through your normal deployment process.

### 6. Create an administrator

```bash
python manage.py createsuperuser
```

Follow the prompts to create the Django superuser account.

### 7. Start the development server

```bash
python manage.py runserver
```

Open the local website:

http://127.0.0.1:8000/

## 🔐 Environment Variables

Configure sensitive values in your local `.env` file and your hosting provider's environment-variable settings.

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django cryptographic key |
| `DEBUG` | Enables or disables Django debug mode |
| `ALLOWED_HOSTS` | Hosts permitted by Django |
| `DATABASE_URL` | Database connection string |
| `EMAIL_HOST` | SMTP server hostname |
| `EMAIL_PORT` | SMTP port |
| `EMAIL_USE_TLS` | SMTP TLS setting |
| `EMAIL_HOST_USER` | Email sender account |
| `EMAIL_HOST_PASSWORD` | Email account App Password |
| `DEFAULT_FROM_EMAIL` | Default sender address |

Add any Cloudinary-specific variables your application requires. In production, use `DEBUG=False`, a strong secret key, and the correct deployed domain.

## 📧 OTP Verification Flow

CampusFind uses separate verification processes for account registration and item handover.

1. A user submits the registration form.
2. CampusFind sends a verification code to the supplied email address.
3. The user enters the code before the new account is activated.
4. The verified user can sign in with their username and password.
5. Claim approval and physical item handover follow their own verification process.

OTP email delivery depends on valid SMTP credentials and a correctly configured email backend.

## 🗄️ Database and Image Storage

### PostgreSQL with Neon
Use PostgreSQL for the deployed application and keep the connection string in an environment variable. A pooled connection may be useful for serverless deployments, depending on your configuration.

### Cloudinary
Configure Cloudinary for uploaded item photographs if enabled in your project settings. Avoid relying on temporary local storage for production user uploads.

## 🌐 Deployment

CampusFind is configured for deployment using Vercel, with Neon PostgreSQL and Cloudinary integrations.

A typical deployment process is:

1. Push the latest code to GitHub.
2. Configure production environment variables.
3. Ensure the production database is correctly configured.
4. Install dependencies during the build.
5. Apply any required database migrations.
6. Verify authentication, OTP email delivery, image uploads, reports, and claims on the deployed site.

Deployment behavior depends on the project's Vercel configuration and Django adapter. Confirm that the production setup supports your application before relying on local development behavior.

## 🧪 Testing Checklist

Before deploying changes, test the following:

- [ ] User registration and email OTP verification.
- [ ] Login with username and password.
- [ ] Correct rejection of unverified account login.
- [ ] Lost-item and found-item report submission.
- [ ] Image uploads and image display.
- [ ] Claim submission and claim review.
- [ ] Handover verification.
- [ ] Role-based access restrictions.
- [ ] Notifications and report status changes.
- [ ] Production database and email configuration.

## 🔒 Security Practices

- Never commit `.env`, database credentials, or email App Passwords.
- Use Django's built-in password hashing and authentication features.
- Protect restricted pages and administrative actions with server-side permissions.
- Use CSRF protection on form submissions.
- Enforce OTP expiry, usage limits, and single-use verification.
- Validate uploaded files and restrict permitted file types and sizes.
- Use `DEBUG=False` in production.
- Back up the production database and test recovery procedures.

## 🔮 Future Enhancements

Potential improvements include:

- Smart matching between lost and found items.
- Advanced search, filtering, and pagination.
- Email alerts for matching reports and claim updates.
- Analytics for administrators.
- Installable Progressive Web App (PWA) support.
- Improved response times and performance monitoring.

## 👨‍💻 Author

**Vedant Verma**

Developer of CampusFind — a college-focused lost-and-found management platform.

GitHub: [Vedant-Verma-tech](https://github.com/Vedant-Verma-tech)

Project Repository: [college-lost-found](https://github.com/Vedant-Verma-tech/college-lost-found)

## 📄 License

No license has been specified yet. Add a `LICENSE` file if you decide to distribute the project under an open-source license.

---

**CampusFind — Helping campus communities reunite people with their lost belongings.**
