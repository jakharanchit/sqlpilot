# Pre-Flight Checklist
**Client:** client_example  
**Database:** VEXA  
**Generated:** 2026-03-21 10:28:39

---

## ⚠ Complete this checklist BEFORE running deploy.sql

**Please confirm each item and sign at the bottom.**

### Database Backup
- [ ] A full database backup has been taken **today**
- [ ] The backup has been verified (restore tested or file confirmed)
- [ ] You know where the backup file is stored

### Environment Check
- [ ] You are connected to the **correct server**: `localhost`
- [ ] You are on the **correct database**: `VEXA`
- [ ] Run this query to verify: `SELECT DB_NAME()` — should return `VEXA`
- [ ] No other users are actively writing to the database

### Application
- [ ] The application (LabVIEW / dashboard) is **closed** on all machines
- [ ] You have notified anyone who uses the system of the maintenance window

### What Is Changing
The following changes will be applied:

- **Migration 001:** optimize: SELECT TOP (1000) [testRequestID]
- **Migration 002:** optimize: SELECT TOP (1000) [testRequestID],[testRequestDate

Full details in `technical_report.md`.

### Rollback Plan
- [ ] You have read `rollback.sql` and know how to run it
- [ ] You understand that running `rollback.sql` will **undo everything** in this package

---

## Sign-Off

By proceeding with the deployment, you confirm all items above are complete.

**Name:** _______________________________

**Date:** _______________________________

**Time started:** _______________________

---

*Once this checklist is complete, proceed to `walkthrough.md`.*