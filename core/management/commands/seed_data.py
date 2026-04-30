"""
Management command: python manage.py seed_data

Creates realistic test data:
  - 6 volunteer users (password: edawn2024)
  - 1 staff/admin user (password: edawn2024)
  - 30 companies across multiple industries
  - Assignments spread across volunteers
  - Contact attempts (some leading to Lost)
  - Visit notes with expansion flags and business lead tracking
  - Badges auto-awarded based on activity

Options:
  --reset   Wipe all existing companies, assignments, and visit data first
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Assignment, Company, ContactAttempt, VisitNote, Message, UserBadge
from core.badges import check_and_award_badges


VOLUNTEERS = [
    ("jsmith",    "Jane",    "Smith",    "jsmith@edawn.org"),
    ("mjohnson",  "Marcus",  "Johnson",  "mjohnson@edawn.org"),
    ("aproctor",  "Alicia",  "Proctor",  "aproctor@edawn.org"),
    ("twilliams", "Tom",     "Williams", "twilliams@edawn.org"),
    ("slee",      "Sara",    "Lee",      "slee@edawn.org"),
    ("dgarcia",   "Diego",   "Garcia",   "dgarcia@edawn.org"),
]

COMPANIES = [
    # (name, address, city, state, zip, phone, email, website, industry, contact_name, contact_title)
    ("Acme Manufacturing",       "100 Industrial Blvd",  "Reno",   "NV", "89501", "775-555-0101", "info@acme.com",       "https://acme.com",       "Manufacturing",   "Robert Hall",    "Plant Manager"),
    ("Sierra Nevada Brewing",    "1075 E 20th St",       "Reno",   "NV", "89512", "775-555-0102", "contact@snbrewing.com","",                      "Food & Beverage", "Lisa Tran",      "Operations Dir."),
    ("Reno Logistics Group",     "2200 Vassar St",       "Reno",   "NV", "89502", "775-555-0103", "",                    "",                       "Transportation",  "Mike Pearson",   "CEO"),
    ("TechBridge Solutions",     "500 E Liberty St",     "Reno",   "NV", "89501", "775-555-0104", "hr@techbridge.com",   "https://techbridge.io",  "Technology",      "Amy Chen",       "HR Director"),
    ("High Desert Health",       "3300 W Plumb Ln",      "Reno",   "NV", "89509", "775-555-0105", "",                    "",                       "Healthcare",      "Dr. Paul Ruiz",  "Medical Director"),
    ("Sparks Steel & Supply",    "800 Marietta Way",     "Sparks", "NV", "89431", "775-555-0106", "sales@sparksss.com",  "",                       "Manufacturing",   "Gary Stone",     "Sales Manager"),
    ("Nevada Solar Partners",    "1400 S Virginia St",   "Reno",   "NV", "89502", "775-555-0107", "info@nvsolar.com",    "https://nvsolar.com",    "Energy",          "Karen Mills",    "President"),
    ("Great Basin Distributors", "610 Spice Islands Dr", "Sparks", "NV", "89431", "775-555-0108", "",                    "",                       "Wholesale",       "James Ford",     "VP Operations"),
    ("Tahoe Financial Group",    "100 W Liberty St",     "Reno",   "NV", "89501", "775-555-0109", "contact@tahoefg.com", "https://tahoefg.com",    "Finance",         "Susan Park",     "Branch Manager"),
    ("Mountain West Realty",     "4895 Double R Blvd",   "Reno",   "NV", "89521", "775-555-0110", "",                    "",                       "Real Estate",     "Chris Dunbar",   "Broker"),
    ("Reno Air Transport",       "2001 E Plumb Ln",      "Reno",   "NV", "89502", "775-555-0111", "ops@renoair.com",     "",                       "Transportation",  "Phil Nguyen",    "Station Manager"),
    ("Basin Mining Co.",         "7200 Longley Ln",      "Reno",   "NV", "89511", "775-555-0112", "",                    "",                       "Mining",          "",               ""),
    ("Neon Valley Media",        "299 S Virginia St",    "Reno",   "NV", "89501", "775-555-0113", "hello@neonvm.com",    "https://neonvm.com",     "Media",           "Tina Ross",      "Creative Dir."),
    ("Silver State Staffing",    "1 E 1st St",           "Reno",   "NV", "89501", "775-555-0114", "",                    "",                       "Staffing",        "Brenda Walsh",   "Recruiter"),
    ("Legends Hospitality",      "255 N Sierra St",      "Reno",   "NV", "89501", "775-555-0115", "gm@legendshotel.com", "https://legendshotel.com","Hospitality",    "Marco Vitale",   "General Manager"),
    ("Western Ag Supply",        "5600 Mill St",         "Sparks", "NV", "89431", "775-555-0116", "",                    "",                       "Agriculture",     "Dale Horton",    "Owner"),
    ("Summit Data Center",       "9350 Gateway Dr",      "Reno",   "NV", "89521", "775-555-0117", "info@summitdc.com",   "https://summitdc.com",   "Technology",      "Rachel Kim",     "Facilities Mgr"),
    ("Clearwater Consulting",    "400 W 4th St",         "Reno",   "NV", "89503", "775-555-0118", "",                    "",                       "Consulting",      "Aaron Bell",     "Principal"),
    ("NV Craft Spirits",         "1045 E 4th St",        "Reno",   "NV", "89512", "775-555-0119", "tours@nvcraft.com",   "",                       "Food & Beverage", "Molly Grant",    "Distillery Mgr"),
    ("Desert Wind Construction", "3800 Barron Way",      "Reno",   "NV", "89511", "", "",                                "",                       "Construction",    "",               ""),
    ("Pioneer Equipment Rental", "1760 E Commercial Row","Reno",   "NV", "89502", "775-555-0121", "",                    "",                       "Equipment Rental","Todd Barnes",    "Owner"),
    ("Alpine Insurance Group",   "10 Liberty St",        "Reno",   "NV", "89501", "775-555-0122", "info@alpineins.com",  "https://alpineins.com",  "Insurance",       "Nancy Flores",   "Agent"),
    ("Reno Print & Design",      "522 W 5th St",         "Reno",   "NV", "89503", "775-555-0123", "",                    "",                       "Printing",        "Kevin Shaw",     "Owner"),
    ("Cascade Tech Partners",    "6900 S McCarran Blvd", "Reno",   "NV", "89509", "775-555-0124", "info@cascadetp.com",  "https://cascadetp.com",  "Technology",      "Yuki Tanaka",    "Director"),
    ("Basin Biomedical",         "1670 Rupert St",       "Reno",   "NV", "89502", "775-555-0125", "",                    "",                       "Healthcare",      "Dr. Maria Soto", "Lab Director"),
    ("Truckee River Brewing",    "1 Stokes St",          "Reno",   "NV", "89501", "775-555-0126", "hello@trbrew.com",    "https://trbrew.com",     "Food & Beverage", "Sam Kowalski",   "Head Brewer"),
    ("NV Fleet Services",        "2300 Harvard Way",     "Reno",   "NV", "89502", "", "",                                "",                       "Transportation",  "",               ""),
    ("Ridgeline Architecture",   "50 Washington St",     "Reno",   "NV", "89503", "775-555-0128", "design@ridgeline.com","https://ridgeline.com",  "Architecture",    "Claire Webb",    "Principal Arch."),
    ("Pyramid Lake Fisheries",   "2100 Pyramid Way",     "Sparks", "NV", "89436", "775-555-0129", "",                    "",                       "Agriculture",     "Tribal Contact", ""),
    ("Washoe County Creamery",   "890 Record St",        "Reno",   "NV", "89512", "775-555-0130", "milk@washoecream.com","",                       "Food & Beverage", "Pete Crawford",  "Owner"),
]


# (notes, follow_up_needed, follow_up_notes,
#  adding_sf, new_building, adding_equipment, capex_planned, expansion_notes,
#  received_lead)
VISIT_DATA = [
    (
        "Met with the operations manager. Company is actively hiring — up 12 employees this quarter. Very interested in EDAWN's workforce development programs.",
        True, "Send workforce training program brochure and invite to next quarterly event.",
        True, False, False, True, "Planning a 8,000 sq ft warehouse addition in Q3. CapEx budget of approx $2M already approved.",
        True,
    ),
    (
        "Spoke with owner directly. Business has grown 20% this year and they are at capacity in their current space. Open to future partnerships.",
        False, "",
        False, True, False, False, "Actively looking at two buildings on Kietzke Ln. Hoping to move within 18 months.",
        False,
    ),
    (
        "Toured the facility. About 45 employees on site. They use local suppliers and expressed interest in our supplier network program.",
        False, "",
        False, False, True, False, "Purchasing two new CNC machines this fall.",
        False,
    ),
    (
        "Quick visit — GM was in a meeting but assistant gave a brief overview. Left materials. They will review and may attend next quarterly event.",
        True, "Circle back in 30 days — GM wanted to connect directly.",
        False, False, False, False, "",
        True,
    ),
    (
        "Great 45-minute conversation with the director. They are planning to expand and want to know more about incentive programs. Very engaged.",
        False, "",
        True, True, True, True, "Major expansion planned: adding 15,000 sq ft, moving to new building, upgrading all production equipment. CapEx estimated $5M+.",
        False,
    ),
    (
        "Visited during lunch service. Owner said things are going well. Small operation, not in immediate need of services but appreciates the outreach.",
        False, "",
        False, False, False, False, "",
        False,
    ),
]

CONTACT_NOTES_TEXTS = [
    "Called main line, no answer. Left voicemail.",
    "Emailed contact — no response after 3 days.",
    "Stopped by — office was closed, left a business card.",
    "Called twice, went to voicemail both times.",
    "Sent follow-up email, no reply.",
    "Attempted in person visit, receptionist said contact was out of office.",
]


class Command(BaseCommand):
    help = "Populate the database with realistic test data"

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete all existing companies, assignments, visit notes, and messages before seeding.',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write("  Resetting existing data...")
            Message.objects.all().delete()
            UserBadge.objects.all().delete()
            VisitNote.objects.all().delete()
            ContactAttempt.objects.all().delete()
            Assignment.objects.all().delete()
            Company.objects.all().delete()
            User.objects.filter(is_staff=False).delete()
            self.stdout.write("  Reset complete.")

        self.stdout.write("Seeding test data...")

        # ----------------------------------------------------------------
        # Admin user
        # ----------------------------------------------------------------
        admin, created = User.objects.get_or_create(
            username='kim',
            defaults=dict(first_name='Kim', last_name='Yaeger', email='kyaeger@edawn.org',
                          is_staff=True, is_superuser=True),
        )
        if created:
            admin.set_password('edawn2024')
            admin.save()
            self.stdout.write("  Admin user 'kim' created")

        # ----------------------------------------------------------------
        # Volunteers
        # ----------------------------------------------------------------
        volunteers = []
        for username, first, last, email in VOLUNTEERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults=dict(first_name=first, last_name=last, email=email),
            )
            if created:
                user.set_password("edawn2024")
                user.save()
            volunteers.append(user)
        self.stdout.write(f"  {len(volunteers)} volunteers ready")

        # ----------------------------------------------------------------
        # Companies
        # ----------------------------------------------------------------
        companies = []
        for row in COMPANIES:
            name, address, city, state, zip_code, phone, email, website, industry, contact_name, contact_title = row
            co, _ = Company.objects.get_or_create(
                name=name,
                defaults=dict(
                    address=address, city=city, state=state, zip_code=zip_code,
                    phone=phone, email=email, website=website, industry=industry,
                    primary_contact_name=contact_name, primary_contact_title=contact_title,
                ),
            )
            companies.append(co)
        self.stdout.write(f"  {len(companies)} companies ready")

        # ----------------------------------------------------------------
        # Assignments — spread companies across volunteers
        # Scenario breakdown across 30 companies:
        #   6  visited  (with varied expansion flags and business leads)
        #   4  lost     (3 contact attempts each)
        #   5  active   with 2 attempts (warning zone)
        #   5  active   with 1 attempt
        #  10  active   with no attempts yet
        # ----------------------------------------------------------------
        if Assignment.objects.exists():
            self.stdout.write("  Assignments already exist — run with --reset to reseed.")
            self.stdout.write(self.style.SUCCESS("Done."))
            return

        import itertools
        vol_cycle = itertools.cycle(volunteers)

        for i, company in enumerate(companies):
            volunteer = next(vol_cycle)

            assignment = Assignment.objects.create(
                company=company,
                volunteer=volunteer,
                assigned_by=admin,
            )

            if i < 6:
                # --- Visited: use VISIT_DATA for varied expansion/lead fields ---
                (notes, follow_up, follow_up_notes,
                 adding_sf, new_building, adding_equip, capex,
                 expansion_notes, lead) = VISIT_DATA[i]
                VisitNote.objects.create(
                    assignment=assignment,
                    visited_by=volunteer,
                    notes=notes,
                    follow_up_needed=follow_up,
                    follow_up_notes=follow_up_notes,
                    expansion_adding_sq_footage=adding_sf,
                    expansion_new_building=new_building,
                    expansion_adding_equipment=adding_equip,
                    expansion_capex_planned=capex,
                    expansion_notes=expansion_notes,
                    received_business_lead=lead,
                )

            elif i < 10:
                # --- Lost (3 attempts) ---
                for j in range(3):
                    ContactAttempt.objects.create(
                        assignment=assignment,
                        attempted_by=volunteer,
                        method=['phone', 'email', 'in_person'][j % 3],
                        notes=CONTACT_NOTES_TEXTS[j % len(CONTACT_NOTES_TEXTS)],
                    )

            elif i < 15:
                # --- Active with 2 attempts (warning zone) ---
                for j in range(2):
                    ContactAttempt.objects.create(
                        assignment=assignment,
                        attempted_by=volunteer,
                        method='phone' if j == 0 else 'email',
                        notes=CONTACT_NOTES_TEXTS[j],
                    )

            elif i < 20:
                # --- Active with 1 attempt ---
                ContactAttempt.objects.create(
                    assignment=assignment,
                    attempted_by=volunteer,
                    method='phone',
                    notes=CONTACT_NOTES_TEXTS[0],
                )

            # i >= 20: active with no attempts yet

        # Award badges based on seeded activity
        for vol in volunteers:
            check_and_award_badges(vol)

        counts = {
            "visited": Assignment.objects.filter(status="completed").count(),
            "lost":    Assignment.objects.filter(status="lost").count(),
            "active":  Assignment.objects.filter(status="active").count(),
        }
        expansion_visits = VisitNote.objects.filter(
            expansion_adding_sq_footage=True
        ).count() + VisitNote.objects.filter(
            expansion_new_building=True
        ).count() + VisitNote.objects.filter(
            expansion_adding_equipment=True
        ).count() + VisitNote.objects.filter(
            expansion_capex_planned=True
        ).count()
        lead_visits = VisitNote.objects.filter(received_business_lead=True).count()

        self.stdout.write(
            f"  Assignments — {counts['visited']} visited, {counts['lost']} lost, {counts['active']} active"
        )
        self.stdout.write(f"  Visit notes with expansion flags: {expansion_visits} flags across {VisitNote.objects.count()} visits")
        self.stdout.write(f"  Visit notes with business lead: {lead_visits}")
        self.stdout.write(self.style.SUCCESS(
            "\nDone! Credentials (all passwords: edawn2024):\n"
            "  Admin : kim\n"
            "  Volunteers: jsmith, mjohnson, aproctor, twilliams, slee, dgarcia"
        ))
