"""
Seed content for the HaMivtzar News Lab.

All content here is FICTIONAL and generic. It intentionally mimics the *shape*
of a real Israeli news portal (a lobby of teasers, a live "writers chat" feed,
a weather sidebar) so the lab is a realistic security-testing target — but it
does not reproduce any real outlet's articles, branding, or assets.
"""

# --- Lobby articles -------------------------------------------------------
# Each article has an integer id. Note `published` and `internal`:
# unpublished drafts are NOT linked from the lobby, but the article endpoint
# looks them up by id anyway -> that is the intentional IDOR (see app.py).
ARTICLES = [
    {
        "id": 1001,
        "title": "מזג אוויר קייצי צפוי להימשך בסוף השבוע",
        "author": "מערכת הלאב",
        "time": "18:28",
        "body": "שרב קל צפוי להתחזק לקראת סוף השבוע. אין המלצות חריגות.",
        "published": True,
        "internal": "",
    },
    {
        "id": 1002,
        "title": "עיריית לב-הארץ אישרה תקציב תחבורה חדש",
        "author": "מערכת הלאב",
        "time": "17:58",
        "body": "מועצת העיר אישרה תוספת קווי אוטובוס. יישום צפוי ברבעון הבא.",
        "published": True,
        "internal": "",
    },
    {
        "id": 1003,
        "title": "נבחרת החובבים המקומית עלתה לגמר",
        "author": "מערכת הלאב",
        "time": "16:16",
        "body": "ניצחון 2:1 העלה את הנבחרת לגמר האזורי שייערך בשבוע הבא.",
        "published": True,
        "internal": "",
    },
    {
        "id": 1004,
        "title": "מדריך צרכנות: איך משווים מחירי חבילות משלוח",
        "author": "מערכת הלאב",
        "time": "14:55",
        "body": "טיפים להשוואת עלויות משלוח בין ספקים שונים.",
        "published": True,
        "internal": "",
    },
    # --- Intentional IDOR target: an embargoed draft, NOT linked anywhere ---
    {
        "id": 1999,
        "title": "[טיוטה תחת אמברגו] מיזוג צפוי בין שתי חברות מקומיות",
        "author": "עורך ראשי",
        "time": "—",
        "body": "טיוטה פנימית. אין לפרסם עד להסרת האמברגו ביום ראשון.",
        "published": False,
        "internal": "embargo-until=SUNDAY; source=confidential; editor-note=DO-NOT-PUBLISH",
    },
]

# --- Live "writers chat" feed --------------------------------------------
# Messages rendered into the lobby. The POST endpoint does NOT sanitize HTML,
# which is the intentional stored-XSS sink (see app.py).
CHAT_MESSAGES = [
    {"id": 5001, "reporter": "כתב/ת הלאב א'", "time": "19:59", "text": "בדיקת מערכת: הפיד עלה."},
    {"id": 5002, "reporter": "כתב/ת הלאב ב'", "time": "19:58", "text": "אין עדכונים חריגים כרגע."},
    {"id": 5003, "reporter": "דסק הלאב", "time": "19:40", "text": "נמשיך לעדכן במהלך הערב."},
]

# --- Fake internal config leaked by the version endpoint ------------------
# Mimics the kind of config/feature-flag/id soup real portals ship inline
# (stormcaster/euda config, uzdbm ids, ss_cid, etc.). All values are fake.
INTERNAL_CONFIG = {
    "app": "hamivtzar-news-lab",
    "version": "1.2.0-lab",
    "buildHost": "int-adm-01.lab.internal",       # info disclosure: internal hostname
    "featureFlags": {"eudaEnableAgent": False, "syncLoad": False, "debug": True},
    "analytics": {"ss_cid": "LAB-c99a4269-161c-4242", "publisher": "n-lab"},
    "apiKey": "LAB_FAKE_KEY_do_not_use_1a2b3c4d",  # secret-looking string (fake)
    "adminHint": "default admin creds are admin/admin on this lab",
}
