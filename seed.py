#Reset the database and load dummy data. Dummy data only, never real people.

from app import app
from models import Client, Project, RevisionRequest, db

with app.app_context():
    db.drop_all()
    db.create_all()

    # Clients
    bakery = Client(name="Sunrise Bakery", email="hello@sunrisebakery.example.com")
    meetup = Client(name="Lagos Tech Meetup", email="team@lagostechmeetup.example.com")
    cafe = Client(name="Green Leaf Cafe", email="orders@greenleafcafe.example.com")
    db.session.add_all([bakery, meetup, cafe])
    db.session.commit()

    # Projects (the last one has no client, as if its client was deleted)
    logo = Project(title="Bakery logo redesign", description="New logo and colour palette",
                   client_id=bakery.id, agreed_revisions=3, status="Active")
    landing = Project(title="Meetup landing page", description="Single page for event sign-ups",
                      client_id=meetup.id, agreed_revisions=2, status="Active")
    menu = Project(title="Cafe menu design", description="Printed menu, A4",
                   client_id=cafe.id, agreed_revisions=1, status="Completed")
    portfolio = Project(title="Portfolio website refresh", description="Client record was removed",
                        client_id=None, agreed_revisions=2, status="On-hold")
    db.session.add_all([logo, landing, menu, portfolio])
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
    ])
    db.session.commit()

    print("Seeded 3 clients, 4 projects and 7 revision requests.")