IT Helpdesk Ticketing System
----------------------------

With Odoo IT Helpdesk Ticketing System, manage and streamline your organization’s internal IT support requests efficiently.

The IT Ticketing module helps organizations track, approve, assign, and resolve IT-related issues through a structured workflow system involving employees, line managers, IT managers, and IT support teams.

Each ticket follows a configurable approval workflow with automated notifications, reminders, escalations, and reporting dashboards to ensure accountability, transparency, and faster resolution times.

Project Tech Stack
------------------

The IT Ticketing module is built using the standard Odoo framework and follows Odoo’s recommended architectural and development practices.

**Backend Framework:** Odoo ORM & Server Actions

**Programming Language:** Python

**Frontend / Views:** XML (Form, Tree, Kanban, Graph, Dashboard Views)

**Email Engine:** Odoo Mail & QWeb Templates

**Scheduler:** Odoo Cron Jobs

**Database:** PostgreSQL

### Versions Used

This project was developed and tested using the following versions:

**Odoo Version:** Odoo 19.0
**Python Version:** Python 3.12
**Database:** PostgreSQL 16

Manage IT Tickets
-----------------

Create and manage IT support tickets for employees across different departments.

Each ticket contains essential details such as ticket type, priority, subject, description, required date, and assigned users.

Track ticket lifecycle stages including Draft, Manager Approval, IT Approval, Assigned, In Progress, and Done.

Automatically calculate resolution time and categorize tickets as Open or Closed for reporting.

Workflow-Based Approval System
------------------------------

Define flexible approval workflows based on ticket type.

Tickets can follow different paths such as:

* Direct assignment to IT team
* Line Manager → IT Manager → IT Support
* IT Manager → IT Support

Each stage ensures proper authorization before ticket processing continues.

Role-Based Access Control
-------------------------

Ensure secure access through role-based permissions.

Line Managers can approve tickets related to their team and in which their approval required.

IT Manager handle IT approvals and assignments.

IT Support Team members can only work on assigned tickets.

Employees can track their own ticket progress through the portal.

Automated Email Notifications
-----------------------------

Stay informed with automated email notifications at every workflow stage.

Employees receive updates when tickets are submitted, approved, assigned, or completed.

Managers receive approval requests instantly.

IT teams receive assignment notifications with full ticket context.

Emails are dynamically generated using Odoo QWeb templates.

Reminder & Escalation System
----------------------------

Automated cron jobs monitor pending tickets and send reminder emails based on configurable intervals.

Consolidated reminders group multiple tickets into a single email per user for better clarity.

Escalation logic ensures overdue tickets are highlighted for managers to take action.

Social Media Access Management
------------------------------

Manage temporary access requests (e.g., social media access) with controlled duration settings.

Access periods can be configured as:

* 3 Months
* 6 Months
* 1 Year
* Custom expiry date

System automatically calculates access start and end dates upon ticket completion.

Reporting & Dashboard
---------------------

Gain insights into IT operations using built-in dashboards and reports.

View:

* Open vs Closed tickets
* Tickets by category/type
* Average processing time
* Tickets solved per IT support person

Graphical views help in monitoring performance and workload distribution.

Centralized Ticket Tracking
---------------------------
All tickets are centrally managed with full audit history in chatter.

Track who approved, rejected, assigned, or completed a ticket.

Every action is logged for transparency and compliance.

Scalable and Maintainable Architecture
--------------------------------------

Business logic is structured using Odoo models and Python compute methods.

Email templates remain separate for easy customization.

Workflow configuration is dynamic and extendable without code changes.


How to Run the Project
----------------------
### 1. Prerequisites

Ensure the following are installed:

**Python:** 3.12
**PostgreSQL:** 16
**Odoo:** 19.0 source code
**Git**
**pgAdmin 4**
**IDE:** PyCharm / VS Code

### 2. Clone Odoo Source Code
git clone https://www.github.com/odoo/odoo --branch 19.0
cd odoo
### 3. Create Custom Addons Folder
mkdir custom_addons

Place the IT Ticketing module inside this folder.

### 4. Configure Database (pgAdmin)
1. Open pgAdmin 4
2. Create new database
3. Name: **it_ticket_db**
4. Owner: **odoo**

Ensure proper privileges are assigned.

### 5. Configure Odoo

Update odoo.conf:

[options]
addons_path = addons,custom_addons
db_host = localhost
db_port = 5432
db_user = odoo
db_password = your_password
### 6. Install Dependencies
pip install -r requirements.txt
### 7. Run Odoo Server
./odoo-bin -c odoo.conf

Access:

http://localhost:8069
### 8. Install IT Helpdesk Module
1. Enable Developer Mode
2. Update Apps List
3. Search: **IT Helpdesk**
4. Click Install
### 9. Configure Scheduler (Cron Jobs)

Ensure Odoo scheduler is active for:

* Ticket reminders
* Social media access expiry notifications

No manual execution required.