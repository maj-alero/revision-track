"""Reset the database and load dummy data. Dummy data only, never real people.
"""
import bcrypt

from app import app
from models import Client, Project, RevisionRequest, User, db


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


with app.app_context():
    db.drop_all()
    db.create_all()

    # Users: Demo logins (dummy passwords, for testing only)
    demo = User(username="demo_freelancer", email="demo@example.com", password_hash=hash_password("Password123!"))
    second = User(username="second_freelancer", email="second@example.com", password_hash=hash_password("Password123!"))
    db.session.add_all([demo, second])
    db.session.commit()

    # Clients (the first three belong to the demo user, the last one to the second user)
    bakery = Client(user_id=demo.id, name="Sunrise Bakery", email="hello@sunrisebakery.example.com")
    meetup = Client(user_id=demo.id, name="Lagos Tech Meetup", email="team@lagostechmeetup.example.com")
    cafe = Client(user_id=demo.id, name="Green Leaf Cafe", email="orders@greenleafcafe.example.com")
    studio = Client(user_id=second.id, name="Blue Door Studio", email="hi@bluedoorstudio.example.com")
    db.session.add_all([bakery, meetup, cafe, studio])
    db.session.commit()

    # Projects (the demo user's last project has no client, as if its client was deleted)
    logo = Project(user_id=demo.id, client_id=bakery.id, title="Bakery logo redesign",
                   description="New logo and colour palette", agreed_revisions=3, status="Active")
    landing = Project(user_id=demo.id, client_id=meetup.id, title="Meetup landing page",
                      description="Single page for event sign-ups", agreed_revisions=2, status="Active")
    menu = Project(user_id=demo.id, client_id=cafe.id, title="Cafe menu design",
                   description="Printed menu, A4", agreed_revisions=1, status="Completed")
    portfolio = Project(user_id=demo.id, client_id=None, title="Portfolio website refresh",
                        description="Client record was removed", agreed_revisions=2, status="On-hold")
    poster = Project(user_id=second.id, client_id=studio.id, title="Event poster",
                     description="A3 poster for the studio opening", agreed_revisions=2, status="Active")
    db.session.add_all([logo, landing, menu, portfolio, poster])
    db.session.commit()

    # Revision requests (is_extra is True once a project is past its agreed limit)
    db.session.add_all([
        RevisionRequest(project_id=logo.id, description="Make the logo bigger", status="Completed"),
        RevisionRequest(project_id=logo.id, description="Try a warmer colour palette", status="Pending"),
        RevisionRequest(project_id=landing.id, description="Change the hero image", status="Completed"),
        RevisionRequest(project_id=landing.id, description="Move the signup button higher", status="Completed"),
        RevisionRequest(project_id=landing.id, description="Add speaker photos to the page", status="Pending", is_extra=True),
        RevisionRequest(project_id=menu.id, description="Resize the menu to A4", status="Completed"),
        RevisionRequest(project_id=menu.id, description="Add an animated intro", status="Rejected", is_extra=True),
        RevisionRequest(project_id=poster.id, description="Swap the headline font", status="Pending"),
    ])
    db.session.commit()

    print("Seeded 2 users, 4 clients, 5 projects and 8 revision requests.")
