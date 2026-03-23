# GPS Platform Rebuild: Use Case Document

**Client:** Disciples Made, Inc.
**Developer:** Paschal Okonkwo
**Version:** 1.0
**Date:** March 20, 2026
**Status:** CONFIDENTIAL

---

## 1. Authentication & Onboarding

### UC-01: New User Registration

| Field | Detail |
|-------|--------|
| **Actor(s)** | Unregistered Individual |
| **Preconditions** | User has a valid email address. User is not already registered in the system. |

**Main Flow:**

1. User navigates to registration page
2. User enters First Name, Last Name, Email, Password, and optionally Phone
3. User selects church affiliation (search existing churches) or chooses "Independent"
4. System validates email uniqueness and field requirements
5. System creates user account with appropriate role (user) and status (active)
6. System sends welcome email with login confirmation
7. User is redirected to personal dashboard

**Alternative / Exception Flows:**

- **A1: Email already exists (active)** — System displays error: "An account with this email already exists. Please log in or reset your password."
- **A2: Email matches deleted/invited record** — System merges accounts, preserves all historical data, logs merge operation
- **A3: Registration via church-specific assessment link** — User is auto-affiliated with that church; skip church selection step

**Postconditions:** User account exists in database. User is logged in and viewing personal dashboard.

---

### UC-02: User Login

| Field | Detail |
|-------|--------|
| **Actor(s)** | Registered User (any role) |
| **Preconditions** | User has an active account. |

**Main Flow:**

1. User navigates to login screen
2. User enters email and password
3. System authenticates credentials
4. System determines user role (independent/member/church admin/master admin)
5. System redirects to appropriate dashboard based on role

**Alternative / Exception Flows:**

- **A1: Invalid credentials** — System displays error with retry option
- **A2: Account locked** — System displays locked message with instructions to contact church admin or support
- **A3: Expired invite token** — System displays "invite expired" with option to request new invite

**Postconditions:** User is authenticated and viewing their role-appropriate dashboard.

---

### UC-03: Admin Upgrade (User to Church Admin)

| Field | Detail |
|-------|--------|
| **Actor(s)** | Independent User or Church Member |
| **Preconditions** | User is logged in. User does not currently have admin role. |

**Main Flow:**

1. User clicks "Upgrade to Church Admin" on their dashboard
2. System displays upgrade form: church name, address, contact info
3. User fills in church details and submits
4. System creates new Church record in database
5. System assigns user as primary admin of that church
6. System initiates Stripe subscription checkout flow
7. User completes payment setup
8. System activates church admin dashboard and generates unique assessment link

**Alternative / Exception Flows:**

- **A1: Stripe payment fails** — System holds church record in pending state; admin dashboard not activated until payment succeeds
- **A2: Church name already exists** — System warns but allows creation (different location)

**Postconditions:** New church exists in system. User has church admin role. Stripe subscription is active. Admin dashboard is accessible.

---

## 2. Church Affiliation

### UC-04: Request to Link with Church

| Field | Detail |
|-------|--------|
| **Actor(s)** | Independent User |
| **Preconditions** | User is logged in. User is not affiliated with any church. |

**Main Flow:**

1. User clicks "Join a Church" on their dashboard
2. System displays searchable list of active churches
3. User selects their church and submits connection request
4. System creates pending affiliation request
5. System notifies church admin(s) of the pending request
6. User sees "Request Pending" status on their dashboard

**Alternative / Exception Flows:**

- **A1: Church admin declines request** — User remains independent; notified of decline
- **A2: User cancels request before admin review** — Request is removed; no notification sent

**Postconditions:** Pending request exists in system. Church admin has been notified.

---

### UC-05: Church Admin Approves/Declines Link Request

| Field | Detail |
|-------|--------|
| **Actor(s)** | Church Admin |
| **Preconditions** | Admin is logged in. One or more pending link requests exist. |

**Main Flow:**

1. Admin navigates to "Pending Requests" section of admin dashboard
2. Admin reviews user details (name, email)
3. Admin clicks "Approve" or "Decline"
4. If approved: system affiliates user with church; all user assessment history becomes visible to admin
5. If declined: user remains independent; system sends decline notification

**Alternative / Exception Flows:**

- **A1: Admin approves but user has since registered with another church** — System blocks and displays conflict message

**Postconditions:** User affiliation status updated. Admin dashboard reflects new member (if approved).

---

### UC-06: Unlink from Church

| Field | Detail |
|-------|--------|
| **Actor(s)** | Church Member |
| **Preconditions** | User is logged in. User is affiliated with a church. |

**Main Flow:**

1. User navigates to profile/church affiliation settings
2. User clicks "Leave Church"
3. System displays confirmation dialog: "This will remove your church admin's access to your assessment data. Continue?"
4. User confirms
5. System removes church_id from user record
6. System immediately revokes church admin's visibility into this user's data
7. User becomes independent

**Alternative / Exception Flows:**

- **A1: User is also a church admin** — System warns that unlinking will also remove admin role; requires explicit confirmation

**Postconditions:** User is independent. Former church admin can no longer see user's data.

---

## 3. Assessment Workflows

### UC-07: Take Assessment (GPS or MyImpact)

| Field | Detail |
|-------|--------|
| **Actor(s)** | Any Logged-in User |
| **Preconditions** | User is logged in. At least one assessment instrument is available. |

**Main Flow:**

1. User clicks "Take Assessment" from dashboard or direct link
2. System displays instrument selector (GPS / MyImpact Equation)
3. User selects instrument
4. System presents first question with progress indicator ("Question 1 of N")
5. User answers each question sequentially; system validates each response before advancing
6. After final question, user clicks "Submit"
7. System runs scoring engine: sums ratings per gift category (top 2 gifts) and per influencing style (top 2 styles)
8. System stores assessment record (raw answers + scored results) as immutable row
9. System emails user a link to their results page
10. System displays result page with scores, definitions, selections, and story responses
11. User returns to dashboard; new assessment appears in history

**Alternative / Exception Flows:**

- **A1: User abandons mid-assessment** — System saves progress as in_progress; user can resume later
- **A2: Session expires during assessment** — System preserves draft; user resumes on next login
- **A3: User accesses via church-specific deep link with Member ID/Church ID params** — System auto-tags the assessment with the provided church context

**Postconditions:** New assessment record exists with status=completed. Results page accessible. Email with results link sent. Dashboard history updated.

---

### UC-08: Retake Assessment

| Field | Detail |
|-------|--------|
| **Actor(s)** | Any Logged-in User |
| **Preconditions** | User has previously completed at least one assessment. |

**Main Flow:**

1. User clicks "Retake Assessment" from dashboard
2. System presents instrument selection (pre-selected to the instrument being retaken)
3. User completes assessment flow (same as UC-07)
4. System creates a NEW assessment record; previous results are preserved unchanged
5. Dashboard now shows both attempts in chronological history

**Alternative / Exception Flows:**

- A1: No changes from UC-07 alt flows

**Postconditions:** Original assessment record unchanged. New assessment record exists. User can compare results over time.

---

### UC-09: View Assessment Results & History

| Field | Detail |
|-------|--------|
| **Actor(s)** | Any Logged-in User |
| **Preconditions** | User is logged in. User has at least one completed assessment. |

**Main Flow:**

1. User navigates to personal dashboard
2. System displays summary cards for most recent assessment per instrument
3. User clicks on an instrument tab to see full history table
4. User clicks a specific row to see detailed results (graph + text interpretation)
5. User optionally uses side-by-side comparison view to diff GPS vs MyImpact or compare across time

**Alternative / Exception Flows:**

- **A1: User has no completed assessments** — Dashboard displays "No assessments yet" with prominent CTA to take first assessment

**Postconditions:** User has viewed their results; no data modified.

---

## 4. Church Admin Operations

### UC-10: Invite Members (Email / CSV)

| Field | Detail |
|-------|--------|
| **Actor(s)** | Church Admin |
| **Preconditions** | Admin is logged in. Church has active subscription. |

**Main Flow:**

1. Admin clicks "Invite Members" on admin dashboard
2. System displays invite modal with two options: manual email entry (batch) or CSV upload
3. Admin enters emails or uploads CSV file
4. System validates email formats and checks for duplicates
5. System sends invitation emails with unique tokens
6. Invite modal shows color-coded status: green (accepted), yellow (sent), red (failed), grey (deleted)
7. Invited users appear in member table with status "Pending"

**Alternative / Exception Flows:**

- **A1: Email already exists as active user** — System shows option to send affiliation request instead
- **A2: CSV contains invalid emails** — System highlights invalid rows; processes valid ones
- **A3: Admin resends invite** — System generates new token, sends fresh email

**Postconditions:** Invitation records created. Emails sent. Pending users visible in admin dashboard.

---

### UC-11: Export Member Data (CSV)

| Field | Detail |
|-------|--------|
| **Actor(s)** | Church Admin or Master Admin |
| **Preconditions** | Admin is logged in. At least one member has assessment data. |

**Main Flow:**

1. Admin clicks "Export" button on admin dashboard
2. System displays export configuration modal: scope (all/filtered/individual), date range, instrument filter
3. Admin selects parameters
4. System shows preview of sample CSV row with field mapping
5. Admin confirms export
6. System generates CSV file (UTF-8, comma-delimited, CRLF) with filename convention [ChurchName]_[Instrument]_[YYYYMMDD].csv
7. File downloads to admin's browser

**Alternative / Exception Flows:**

- **A1: Export times out** — System shows error modal with troubleshooting steps
- **A2: No data matches filters** — System shows "No records match your criteria" message

**Postconditions:** CSV file downloaded. Export action logged in audit trail.

---

### UC-12: Promote/Demote User Role

| Field | Detail |
|-------|--------|
| **Actor(s)** | Church Admin (within own church) or Master Admin (any church) |
| **Preconditions** | Admin is logged in. Target user is affiliated with admin's church (or any church for master). |

**Main Flow:**

1. Admin opens member detail panel for target user
2. Admin clicks "Make Admin" or "Remove Admin"
3. System displays confirmation dialog showing the action and affected user
4. Admin confirms
5. System updates user role
6. System logs the role change in audit trail
7. Affected user's dashboard updates on next page load

**Alternative / Exception Flows:**

- **A1: Admin attempts to self-demote** — System blocks action: "You cannot remove your own admin role"
- **A2: Demoted admin is the only admin for their church** — System warns: "This church will have no admin. Consider promoting another user first."

**Postconditions:** User role updated. Audit trail entry created.

---

## 5. Master Admin Operations

### UC-13: Impersonate User Account

| Field | Detail |
|-------|--------|
| **Actor(s)** | Master Admin |
| **Preconditions** | Master admin is logged in. |

**Main Flow:**

1. Master admin searches for target user or church
2. Master admin clicks "Impersonate" on target account
3. System displays mandatory reason field: admin must explain why impersonation is needed
4. Admin enters reason and confirms
5. System opens a secure pop-out window showing the platform as the target user sees it
6. System logs impersonation event: master admin ID, target user ID, timestamp, stated reason
7. Master admin performs troubleshooting actions
8. Master admin closes pop-out window to end impersonation

**Alternative / Exception Flows:**

- **A1: Target user is deleted** — System allows impersonation but displays "Deleted User" warning banner

**Postconditions:** Impersonation session logged in audit trail. Any changes made during impersonation are attributed to master admin in audit log.

---

### UC-14: Manage Church Accounts

| Field | Detail |
|-------|--------|
| **Actor(s)** | Master Admin |
| **Preconditions** | Master admin is logged in. |

**Main Flow:**

1. Master admin views system-wide church table with metrics (active users, assessments, last activity)
2. Master admin can add new church records, assign admins, or deactivate churches
3. Master admin can resolve affiliation conflicts (e.g., user linked to wrong church)
4. All actions require explicit confirmation
5. All actions logged in audit trail

**Alternative / Exception Flows:**

- **A1: Removing the only admin from a church** — System requires assigning a replacement before removal

**Postconditions:** Church records updated. Audit trail entries created.

---

## 6. Billing & Subscription

### UC-15: Manage Subscription (Church Admin)

| Field | Detail |
|-------|--------|
| **Actor(s)** | Church Admin |
| **Preconditions** | Admin is logged in. Church has a Stripe customer record. |

**Main Flow:**

1. Admin navigates to "Subscription & Billing" section of admin dashboard
2. System displays current plan (monthly/annual), next billing date, and payment method on file
3. Admin can update payment method (redirects to Stripe-hosted form)
4. Admin can switch between monthly and annual plans
5. Admin can cancel subscription (with confirmation dialog warning of feature loss)
6. System syncs all changes with Stripe and updates local subscription_status

**Alternative / Exception Flows:**

- **A1: Payment method update fails** — System shows Stripe error; retains existing method
- **A2: Subscription lapses (past_due)** — System displays warning banner; admin dashboard remains accessible for 14-day grace period, then read-only

**Postconditions:** Stripe subscription updated. Local database reflects new status.

---

## 7. Data & Privacy

### UC-16: Merge Duplicate User Accounts

| Field | Detail |
|-------|--------|
| **Actor(s)** | System (automatic) or Master Admin (manual) |
| **Preconditions** | A new registration email matches an existing deleted or invited record. |

**Main Flow:**

1. System detects email match during registration or invite
2. System merges church affiliations and assessment records into the most recent/most complete profile
3. System preserves all historical assessment data from both records
4. System logs the merge: old user ID, new user ID, timestamp, reason code
5. Merged user sees consolidated history on their dashboard

**Alternative / Exception Flows:**

- **A1: Conflicting church affiliations (user was in Church A, new record for Church B)** — System flags for master admin manual resolution instead of auto-merging
- **A2: Master admin manually triggers merge** — Same flow, but with explicit admin confirmation and reason entry

**Postconditions:** Single user record exists. All historical data preserved. Merge logged in audit trail.
