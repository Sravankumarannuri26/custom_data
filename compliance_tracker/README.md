Compliance Tracker
------------------

With Odoo Compliance Tracker, manage and monitor your organization’s
regulatory and statutory obligations efficiently.

The Compliance Tracker helps ensure that critical compliance activities are
completed on time by tracking due dates, assigning responsibilities, and
automating reminders and escalations.

Each compliance need is managed through structured tasks, projects, and
automated notifications to maintain accountability and reduce risk.

Project Tech Stack
------------------

The Compliance Tracker module is built using the standard Odoo framework and
follows Odoo’s recommended architectural and development practices.

**Backend Framework:** Odoo ORM & Server Actions

**Programming Language:** Python

**Frontend / Views:** XML (QWeb, Form, Tree, Kanban)

**Email Engine:** Odoo Mail & QWeb Templates

**Scheduler:** Odoo Cron Jobs

**Database:** PostgreSQL

### Versions Used

This project was developed and tested using the following versions:

**Odoo Version:** Odoo 19.0

**Python Version:** Python 3.12

**Database:** PostgreSQL 16

Manage Compliance Tasks
-----------------------

Create and organize compliance tasks across different projects and regulatory
domains. Each task contains essential details such as due dates, assignees,
managers, and reporting status.

Track task progress with clear statuses like In Progress, Overdue, and
Completed, ensuring full visibility for all stakeholders.

Automatically calculate remaining or overdue days based on task due dates.

Assign Responsibilities
-----------------------

Assign compliance tasks to one or multiple users to ensure shared
responsibility and accountability.

Define managers for oversight and escalation, allowing higher-level visibility
into overdue or critical compliance items.

Ensure that all assigned users are notified in a timely and consistent manner.

Automated Compliance Reminders
------------------------------

Stay ahead of deadlines with automated email reminders sent on predefined
trigger days (e.g., 7, 5, 2 days before due date and after overdue).

Users receive consolidated reminders, grouping all relevant compliance
tasks into a single email for better clarity and reduced inbox noise.

Email content is dynamically generated with task details such as project,
status, due date, and days remaining.

Manager Escalation for Overdue Tasks
------------------------------------

Ensure accountability through automatic escalation of overdue compliance tasks
to assigned managers.

Managers receive summarized notifications listing overdue tasks along with
assignees and delay duration, enabling quick corrective action.

This escalation mechanism reduces compliance risk and improves governance.

Clear and Human-Readable Communication
--------------------------------------

System-generated emails present compliance data in a clean, tabular format
that is easy to read and understand.

Technical status values are automatically converted into human-friendly labels
(e.g., In Progress instead of in_progress, Overdue instead of
overdue).

All communication follows a professional and consistent format aligned with
corporate standards.

Centralized Compliance Oversight
--------------------------------

Get a consolidated view of compliance activities across projects and teams.

Identify bottlenecks, overdue items, and high-risk areas quickly through
structured task tracking.

Reduce dependency on manual follow-ups and spreadsheets by centralizing
compliance operations within Odoo.

Scalable and Maintainable Design
--------------------------------

Business logic is handled in Python for clarity, maintainability, and future
scalability.

Email templates remain simple and presentation-focused, ensuring stability and
ease of customization.

The module is designed to adapt easily to additional compliance rules,
workflows, and notification strategies.

How to Run the Project
----------------------

### 1. Prerequisites

Ensure the following are installed on your system:

**Python:** 3.12

**PostgreSQL:** 16

**Odoo:** 19.0 source code

**Git**

**pgAdmin 4** (for database management)

**IDE:** PyCharm / VS Code (recommended for Run/Debug configuration)

### 2. Clone the Odoo Source Code

Clone the Odoo 19 source code (if not already available):

git clone https://www.github.com/odoo/odoo --branch 19.0
cd odoo

### 3. Create Custom Addons Folder

Inside the Odoo root directory, create a folder for custom modules:

mkdir custom_addons


This folder will hold all custom-developed modules, including
Compliance Tracker.

### 4. Create the Module Folder

Inside custom_addons, place your module:

Ensure the module folder name matches the name used in
__manifest__.py.

### 5. Create Database Using pgAdmin

Instead of using command-line tools, create the database via pgAdmin:

1. Open **pgAdmin 4**
2. Connect to your PostgreSQL server
3. Right-click **Databases** → **Create** → **Database**
4. Enter:
5. **Database Name:** compliance_db
6. **Owner:** odoo
7. Click **Save**
Ensure the odoo user has full privileges on the database.

### 6. Configure Odoo

Create or update your odoo.conf file:

[options]
addons_path = addons,custom_addons
db_host = localhost
db_port = 5432
db_user = odoo
db_password = your_password


### **Important:**

custom_addons must be included in addons_path, otherwise Odoo will
not detect the Compliance Tracker module.

### 7.  Setup Python Interpreter (Run/Debug Configuration) Using PyCharm 

1. Open the **Odoo root folder** in PyCharm
2. Go to **Settings** → **Python Interpreter**
3. Select **Python 3.11**
4. Preferably from a virtual environment

#### Install required dependencies:

pip install -r requirements.txt

#### Configure Run/Debug

Go to **Run → Edit Configurations**

Add a new **Python configuration**

Set the following:
    **Script path:** odoo-bin
    **Parameters:** -c odoo.conf
    **Python Interpreter:** Python 3.11
    **Working directory:** Odoo root folder

Save the configuration

This allows you to run and debug Odoo directly from the IDE.

## 8. Run Odoo Server

Using terminal:

./odoo-bin -c odoo.conf

Or using IDE:

Click Run or Debug in your configured Run/Debug profile

Once started, access Odoo at:

http://localhost:8069

## 9. Install the Compliance Tracker Module

1. Log in to Odoo
2. Enable Developer Mode
3. Navigate to Apps
4. Click Update Apps List
5. Search for Compliance Tracker
6. Click Install

### 10. Configure Cron Jobs

Ensure Odoo’s scheduler (cron) is enabled

The Compliance Task Reminder Cron runs automatically based on its
configured interval

No manual triggering is required once installed