# EDAWN Business Builders Portal — Implementation Plan
**Based on:** Software Requirements Document v1.2 (April 2026)
**Branch:** `claude/review-project-requirements-KZQrn`

---

## Priority Legend
- 🔴 **P0** — July 1 hard deadline (must ship first)
- 🟠 **P1** — High priority, ship immediately after P0
- 🟡 **P2** — Medium priority, next cycle
- 🔵 **P3** — Low priority / blocked on external input

---

## Phase 1 — July 1 Blockers (P0)

These two features must be live before the new industry-specific assignment model goes live.

### F-32 · Expansion opportunity fields on visit form
**Req:** Structured checkboxes on the VisitNote form — not freeform text.

- [ ] Add 5 Boolean fields to `VisitNote` model:
  - `expansion_adding_sq_footage`
  - `expansion_new_building`
  - `expansion_adding_equipment`
  - `expansion_capex_planned`
  - `received_business_lead` *(combines F-35 here — same form, same migration)*
- [ ] Add `expansion_notes` TextField (blank=True) for optional detail
- [ ] Create and apply migration
- [ ] Update `VisitNoteForm` — add all new fields with checkbox widgets; group under an "Expansion & Opportunities" fieldset
- [ ] Update `log_visit.html` — render expansion checkboxes section; keep follow-up toggle JS intact
- [ ] Update `company_detail.html` — show expansion flags in visit history cards (icons/badges per flag set)
- [ ] Update Django admin `VisitNoteInline` — surface new fields as readonly columns

### F-35 · Volunteer business lead tracking per visit
*Handled inside F-32 migration above (`received_business_lead` field on VisitNote).*

- [ ] Add "Did you receive a business lead or referral from this visit?" checkbox to visit form
- [ ] Surface lead count on volunteer's dashboard stat cards

### F-07 · Industry grouping / filtering view
**Req:** Companies filterable by industry group in the volunteer view; Kim needs this for July 1 assignment transition.

- [ ] Update `company_list` view — add `industry` as a filter parameter alongside existing `status` filter
- [ ] Update `company_list.html` — add industry filter dropdown (populated from distinct industry values on user's assignments)
- [ ] Update admin company list — add industry column to staff quick-assign view and admin dashboard company table
- [ ] Verify `CompanyAdmin` list_filter already includes `industry` ✓ (confirm in admin.py)

---

## Phase 2 — High Priority (P1)

Ship these immediately after Phase 1.

### F-10 / F-11 · Complete visit log fields
**Req:** Visit form must capture structured fields matching the EDAWN Company Snapshot form.

- [ ] Add required fields to `VisitNote` model:
  - `contact_name` (CharField, blank=True) — person spoken to at the company
  - `employee_count` (PositiveIntegerField, null=True, blank=True)
  - `hiring_status` (CharField, choices: hiring / layoffs / stable / unknown, required)
  - `expansion_plans_notes` (TextField, blank=True) — freeform detail beyond the F-32 checkboxes
- [ ] Create and apply migration
- [ ] Update `VisitNoteForm` — add fields; mark `hiring_status` required
- [ ] Update `log_visit.html` — render new fields; group logically (Who did you meet? → Workforce → Expansion)
- [ ] Update `company_detail.html` — display new fields in visit history

### F-33 · Certified Business Builder Volunteer (BBV) designation
**Req:** Award at 3 months of active volunteering; badge + notification to Kim and volunteer.

- [ ] Add `bbv_certified` BooleanField and `bbv_certified_date` DateTimeField to `User` profile (via a `UserProfile` model or extend with a one-to-one, or use an existing approach — check if a profile model exists first)
- [ ] Create "Certified Business Builder Volunteer" Badge record in a data migration (criteria_type='manual', so it won't auto-award from the existing logic)
- [ ] Write `check_bbv_eligibility(user)` function in `badges.py`:
  - Active volunteering = has at least one `VisitNote` in each of the last 3 calendar months
  - If eligible and not yet certified: award BBV badge, set `bbv_certified=True/date`, send notification message to Kim (private Message), send congratulatory Message to volunteer
- [ ] Hook `check_bbv_eligibility` into `VisitNote.save()` after `check_and_award_badges()`
- [ ] Surface BBV designation on volunteer's dashboard and on the leaderboard row
- [ ] Surface BBV designation in Django admin volunteer list

### F-34 · Expansion opportunity aggregate admin view
**Req:** Kim needs to see all expansion signals in one place, not buried in visit notes.

- [ ] Add "Expansion Signals" page at `/admin-actions/expansion-signals/` (staff_member_required)
- [ ] View queries all VisitNotes where any expansion flag is True, ordered by visit_date desc
- [ ] Template shows: Company, Volunteer, Visit Date, which flags are set, expansion_notes — filterable by date range and industry
- [ ] Add "Expansion Signals" quick-action link to admin dashboard and Django admin index

### F-18 · Surface last login + last visit date in admin volunteer view
**Req:** Kim needs last login and last submission visible without clicking into each user.

- [ ] Extend `CustomUserAdmin` list_display to include: `last_login`, `last_visit_date` (custom method), `visit_count` (custom method), `is_active`
- [ ] `last_visit_date`: annotate queryset with `Max('assignments__visit_notes__visit_date')`
- [ ] `visit_count`: annotate with count of completed assignments
- [ ] Add `list_filter` for `last_login` and `is_active`

### F-19 · Inactivity flagging in admin
**Req:** Flag volunteers for Kim's review when inactive; no auto-deactivation.

- [ ] Add inactivity threshold logic: volunteer is "flagged" if last visit date > 45 days ago AND they have active assignments
- [ ] Show flag indicator (⚠️ warning icon) in `CustomUserAdmin` list via `inactivity_flag` computed column
- [ ] Add "Overdue Volunteers" count to Django admin index dashboard stats
- [ ] Add "Companies not visited in 60+ days" count to Django admin index dashboard stats

### F-03 · Training completion tracking
**Req:** Track whether each volunteer has completed training and when.

- [ ] Add `training_completed` BooleanField (default=False) and `training_completed_date` DateField (null=True, blank=True) to User (via profile or direct extension)
- [ ] Surface in `CustomUserAdmin` list_display and list_filter
- [ ] Make it editable inline so Kim can check it off per volunteer

### F-28 · Volunteer roster with training status indicator
**Req:** Admin volunteer list shows active/inactive/training-pending status.

- [ ] Depends on F-03 (training_completed field)
- [ ] Add computed `volunteer_status` column to `CustomUserAdmin`: "Training Pending" / "Active" / "Inactive (flagged)"
- [ ] Filter options: show only training-pending, show only inactive

### F-27 · Admin dashboard — missing metrics
**Req:** Add "companies not visited in 60+ days" and "overdue volunteers" to the admin index.

- [ ] Update `AdminSite.index()` context in `admin.py`:
  - `companies_not_visited_60d`: Companies with status='visited' or 'assigned' where latest visit_note > 60 days ago or never
  - `overdue_volunteers`: Active volunteers with no visit in 45+ days
- [ ] Update `admin/index.html` — add stat cards for both new metrics

---

## Phase 3 — Medium Priority (P2)

### F-02 · Training scheduling link embed
**Req:** Simple calendar link (not Calendly integration) for booking a training session.

- [ ] Add `TRAINING_CALENDAR_URL` setting in `settings.py` (read from env var, fallback to `""`)
- [ ] Surface on volunteer dashboard (conditionally, if `not user.profile.training_completed`)
- [ ] Surface on admin invite page so Kim can include it when sending invite codes

### F-04 · Resource library
**Req:** Visit scripts, company snapshot form, workforce guides, EDAWN value prop materials.

- [ ] Add `Resource` model: `title`, `description`, `url` (external link or uploaded file), `category` (CharField choices: visit_script / snapshot_form / workforce_guide / value_prop / other), `sort_order`, `is_active`
- [ ] Create migration
- [ ] Add `ResourceAdmin` so Kim can manage resources without dev involvement
- [ ] Add `/resources/` view (login_required) listing resources grouped by category
- [ ] Add "Resources" link to sidebar nav in `base.html`
- [ ] Add resource library link to volunteer dashboard

### F-14 · Export visit data
**Req:** CSV export filterable by date range, industry, and volunteer.

- [ ] Add `/admin-actions/export-visits/` view (staff_member_required)
- [ ] Form inputs: date_from, date_to, industry (select), volunteer (select), format (CSV)
- [ ] Export columns: Visit Date, Company, Industry, Volunteer, Contact Name, Employee Count, Hiring Status, Expansion Flags, Notes, Follow-up Needed
- [ ] Add export link to Django admin index and admin-actions nav

### F-31 · Export full visit history
*Covered by F-14 with no volunteer filter applied (admin sees all).*

### F-21 · Filtered group messaging
**Req:** Kim can send a message to all volunteers or a filtered subset (e.g., by industry group).

- [ ] Update `MessageForm` — add optional `recipient_group` field (choices: all_volunteers / by_industry / specific_volunteer)
- [ ] Add `recipient_industry` and `recipient_user` conditional fields
- [ ] Update `message_create` view — if recipient_group is set and sender is staff, fan out to individual private Messages per matched volunteer
- [ ] Update `message_create.html` — show/hide recipient fields based on group selection (JS toggle)

### F-22 · Templated messages
**Req:** Pre-loaded starting templates for common scenarios.
**Blocked on:** Q-02 (get 2–3 Word templates from Kim before building)

- [ ] (After Q-02 resolved) Add `MessageTemplate` model: `name`, `subject`, `body`, `is_active`
- [ ] Seed with Kim's templates via data migration
- [ ] Add template selector to `message_create` form — selecting one pre-fills subject/body (JS)
- [ ] Add `MessageTemplateAdmin` for Kim to manage templates

---

## Phase 4 — Notifications (P1 after SendGrid setup)

**All items in this phase are blocked until SendGrid is configured on Render.**
Setup steps: Add `SENDGRID_API_KEY` env var on Render → install `django-sendgrid-v5` → configure `EMAIL_BACKEND` in `settings.py`.

### F-15 · Auto-reminder to volunteer at 30 days inactive

- [ ] Configure SendGrid email backend in `settings.py`
- [ ] Write management command `send_inactivity_reminders` — queries volunteers with active assignments and no visit in 30+ days, sends reminder email
- [ ] Set up Render cron job to run command daily
- [ ] Email template: remind volunteer of their active assignments, link to portal

### F-16 · Notify Kim when volunteer inactive 45+ days

- [ ] Extend `send_inactivity_reminders` command — separately notify Kim (staff users) when any volunteer crosses the 45-day threshold (send once, track with a `last_inactivity_notified` field)

### F-17 · Notify Kim when visit submitted

- [ ] In `VisitNote.save()`, after existing hooks, call `notify_staff_visit_submitted(visit_note)`
- [ ] Function emails all `is_staff=True` users: company name, volunteer name, visit date, link to admin assignment view

---

## Open Questions (do not build until resolved)

| ID | Question | Blocks |
|----|----------|--------|
| Q-02 | What are Kim's 2–3 post-visit email templates? | F-22 |
| Q-05 | Who is the secondary admin (Veronica)? Does she need a login? | F-03, admin setup |

---

## Suggested Build Order

```
Week 1:  F-32 + F-35 (visit form expansion fields + lead tracking)
         F-07 (industry filter)
         → Ship Phase 1

Week 2:  F-10/F-11 (complete visit fields)
         F-18 + F-19 (admin volunteer metrics + inactivity flag)
         F-27 (admin dashboard missing metrics)

Week 3:  F-33 (BBV certification logic)
         F-34 (expansion signals admin view)
         F-03 + F-28 (training tracking + roster status)

Week 4:  F-02 (training link)
         F-04 (resource library)
         F-14/F-31 (data export)

After SendGrid configured:
         F-15, F-16, F-17 (notifications)

After Q-02 resolved:
         F-21, F-22 (filtered messaging + templates)
```

---

## Notes

- User profile extension: Before adding `training_completed`, `bbv_certified`, etc., check if a `UserProfile` model is the right approach vs. a proxy model. Keep it simple — a `UserProfile` one-to-one linked to `User` is cleanest.
- All new views follow existing patterns: `@login_required` for volunteers, `@staff_member_required` for admin actions.
- All new forms follow existing Bootstrap 5.3 widget styling in `forms.py`.
- No JavaScript frameworks — keep all interactivity as simple HTML toggles or minimal vanilla JS, consistent with the rest of the codebase.
- No Salesforce sync, no Calendly integration — explicitly out of scope per Section 7.
