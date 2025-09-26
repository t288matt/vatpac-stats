# How Canonical Processing Works - Plain English Guide

## What is Canonical Processing?

Canonical processing is like a smart organizer that takes all the messy flight data and creates clean, organized summaries. Think of it as taking a pile of scattered flight records and turning them into neat, complete flight summaries that tell the whole story of each flight.

## The Big Picture

The system has two main parts:
1. **The Session Selector** - finds completed flights that need summaries
2. **The Canonical Processor** - creates or updates the flight summaries

## How It Works Step by Step

### Step 1: Finding Completed Flights (Session Selector)

The system looks for flights that are "complete" - meaning they happened at least 8 hours ago. It searches through two places:
- The main flights table (recent flights)
- The flights archive table (older flights that were moved there)

**What makes a flight "complete"?**
- The flight must have ended at least 8 hours ago
- The system looks at the last time the flight was updated in the database

**How does it group flight records?**
- It groups records by: callsign (like "QFA123"), pilot ID, departure airport, and arrival airport
- If there's a gap of more than 2 hours between flight records, it treats them as separate sessions
- This prevents mixing up different flights that might have the same callsign

**What does it return?**
- For each completed flight, it gives back:
  - When the flight started (session_start)
  - When the flight ended (session_end) 
  - The latest departure time
  - The latest route information

### Step 2: Processing Each Flight (Canonical Processor)

For each completed flight found by the session selector, the system tries to create or update a flight summary.

**First, it tries to update an existing summary:**
- It looks for an existing summary that matches the flight details
- If it finds one, it updates it with new information
- It uses the session_end time as the completion time

**If no existing summary is found:**
- It creates a new summary with all the flight details
- It fills in information like aircraft type, pilot name, flight rules, etc.
- It calculates how long the pilot was online
- It figures out which air traffic control sectors the flight passed through

**What information gets stored?**
- Basic flight info: callsign, departure, arrival, route
- Pilot info: name, ID, ratings
- Aircraft info: type, planned altitude, flight rules
- Time info: when they logged on, when they logged off, total time online
- Air traffic control info: which sectors they flew through, how long in each sector

### Step 3: Running Automatically

The system runs this process automatically every few minutes:
- It processes up to 5000 flights at a time (to avoid overwhelming the database)
- It always processes the 5000 most recent completed flight sessions
- If it finds 5000 or more flights to process, it takes a short break (1 minute) and runs again
- If it finds fewer than 5000 flights, it takes a longer break (15 minutes) before checking again

## The Problem We Discovered

Through extensive investigation, we discovered the system has **multiple processing paths** running simultaneously, creating complexity and inconsistent behavior:

### Multiple Processing Systems Running at Once

**The Real Issue:** The system doesn't have just one processing method - it has several:

1. **API Endpoint Processing** - When you manually trigger processing
2. **Scheduled Background Task** - Runs automatically every 60 minutes  
3. **Legacy Processing Methods** - Old code that's partially disabled but still exists
4. **Enrichment Processing** - Separate system for adding controller interaction data

### Different Flights, Different Processors

**What we found:**
- **Recent flights** (like QTR90K) are processed by the API endpoint → Aircraft fields work correctly
- **Older archived flights** (like JST458) are processed by the scheduled background task → Aircraft fields remain empty
- Each processing path handles different subsets of flights
- The scheduled task processes about 1,400 flights while the API processes about 2,100 different flights

### The Archive Table Problem

**The specific issue:**
- Flights older than a certain time get moved to the `flights_archive` table
- The scheduled background task tries to process these archived flights
- Despite our fixes working perfectly when tested manually, they fail in the scheduled task environment
- This means older flights don't get complete aircraft information (type, registration, etc.)

### Why This Matters

**The intended design:** Canonical processing was supposed to simplify everything into one reliable system
**The reality:** Multiple processing systems create:
- Unpredictable behavior (which processor will handle your flight?)
- Inconsistent data (recent flights complete, older flights missing data)  
- Complex debugging (had to trace through multiple systems to find the problem)
- Maintenance burden (fixes need to work across multiple systems)

## The Solution

The solution has two parts:

### Immediate Fix: Archive Table Processing
- Fix why the archive table query fails in the scheduled background task
- Even though the SQL query works perfectly when tested manually, it fails in production
- This will ensure older flights get complete aircraft information

### Long-term Fix: Simplify the Architecture
- **Complete the canonical processing migration** - Make sure all flights go through one reliable system
- **Remove the multiple processing paths** - Eliminate the complexity that causes unpredictable behavior
- **Standardize the processing** - Whether it's a recent flight or an archived flight, it should work the same way

## In Simple Terms

Think of it like this:

**The Current Situation:**
- You have multiple filing systems for the same information
- Some clerks file recent documents in one system (works great)
- Other clerks file old documents in a different system (missing information)
- You never know which clerk will handle your document
- The systems don't work the same way

**The Solution:**
- **Immediate**: Fix the broken filing system so old documents get complete information
- **Long-term**: Have just one filing system that works reliably for all documents
- **Result**: Every document gets filed completely and consistently, no matter when it was created

This way, whether your flight happened yesterday or last month, it will have complete information including aircraft type, pilot details, and all other relevant data.
