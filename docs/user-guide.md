# CIRA User Guide

A guide to using CIRA (Company Intelligence Research Assistant) for automated company research.

## Getting Started

### 1. Access the Application

Open your browser and navigate to:
- Local development: `http://localhost:5173`
- Production: Your deployment URL

### 2. Dashboard Overview

The dashboard is your main workspace. Here you can:
- View all companies you've researched
- Filter by status (Pending, In Progress, Completed, Failed, Paused)
- Search companies by name
- Sort by various fields
- Access company details, progress, and exports

## Adding a Company

### Single Company

1. Click **"Add Company"** button on the dashboard
2. Fill in the form:
   - **Company Name** (required): The company's name
   - **Website URL** (required): Company's main website (e.g., `https://acme.com`)
   - **Industry** (optional): Industry category
3. (Optional) Expand **Advanced Options** to configure:
   - **Analysis Mode**: Quick (faster, fewer pages) or Thorough (comprehensive)
   - **Max Pages**: Maximum pages to crawl (default: 100)
   - **Max Depth**: How many links deep to follow (default: 3)
   - **Time Limit**: Maximum crawl time in minutes (default: 30)
   - **External Links**: Toggle following LinkedIn, Twitter, Facebook profiles
4. Click **"Start Analysis"**

### Batch Upload

For multiple companies:

1. Click **"Batch Upload"** on the dashboard
2. **Download Template**: Get the CSV template
3. Fill in the template with your companies:
   ```csv
   company_name,website_url,industry
   Acme Corp,https://acme.com,Technology
   Widget Inc,https://widget.io,Manufacturing
   ```
4. Drag and drop your CSV or click to upload
5. Review the preview table:
   - Green rows: Valid entries
   - Red rows: Invalid entries with error messages
6. Click **"Upload Valid Rows"**

## Monitoring Progress

When analysis starts, you'll see the progress page:

### Progress Indicators

- **Progress Bar**: Overall completion percentage
- **Phase**: Current processing phase
  - Queued → Crawling → Extracting → Analyzing → Generating → Completed
- **Stats Grid**:
  - Pages Crawled: Number of pages processed
  - Entities Found: People, companies, products identified
  - Tokens Used: Claude API tokens consumed
- **Time**: Elapsed and estimated remaining time
- **Current Activity**: What's happening right now

### Controls

- **Pause**: Stop analysis (can resume later)
- **Cancel**: Stop and mark as failed

### Auto-Redirect

When complete, you'll automatically go to the results page.

## Viewing Results

### Summary Tab

The executive summary and detailed analysis sections:
- **Executive Summary**: 3-4 paragraph overview
- **Company Overview**: Founding, headquarters, size, industry
- **Business Model & Products**: Revenue model, key products
- **Team & Leadership**: Key executives and founders
- **Market Position**: Target market, differentiators
- **Key Insights**: Notable observations
- **Red Flags**: Potential concerns

### Entities Tab

All extracted entities with:
- **Type**: Person, Organization, Product, Location, etc.
- **Value**: The entity name/text
- **Confidence**: How confident the extraction is (0-100%)
- **Source**: Which page it was found on

Filter by entity type or search by value.

### Pages Tab

All crawled pages with:
- **Type**: About, Team, Product, Contact, etc.
- **URL**: Page address
- **Crawled At**: When it was processed

Filter by page type.

### Token Usage Tab

API usage breakdown:
- **Total Tokens**: Input + Output tokens
- **Cost Estimate**: Approximate cost
- **By Section**: Which analysis sections used how many tokens

### Sidebar

Quick info about the company:
- Name, website, industry
- Analysis date and mode
- Pages analyzed, entities found
- Version number

## Exporting Results

Click the **"Export"** dropdown to download:

- **Markdown (.md)**: Simple text format
- **Word (.docx)**: Microsoft Word document
- **PDF (.pdf)**: Printable PDF report
- **JSON (.json)**: Full data export (includes raw data option)

## Managing Analyses

### Re-scanning

For completed companies:
1. Click **"Re-scan"** on the results page
2. Confirm the action
3. New analysis starts as version 2

CIRA keeps up to 3 versions per company.

### Comparing Versions

1. Go to **Versions** tab
2. Select two versions to compare
3. View changes highlighted:
   - Green: Added
   - Red: Removed
   - Yellow: Modified

### Pausing and Resuming

If you need to pause:
1. Click **"Pause"** on the progress page
2. Analysis stops and saves checkpoint
3. Click **"Resume"** to continue

Checkpoints preserve:
- Pages visited (won't re-crawl)
- Queue position
- Entities extracted

### Deleting

1. From dashboard, click delete icon on a company row
2. Confirm deletion
3. Company and all data permanently removed

## Configuration

Access **Settings** from the navigation:

### Default Settings

- **Analysis Mode**: Quick or Thorough default
- **Max Pages**: Default page limit
- **Max Depth**: Default crawl depth
- **Time Limit**: Default time limit
- **External Links**: Default social media following

### Mode Presets

Click preset buttons to quickly apply:
- **Quick**: 20 pages, depth 2
- **Thorough**: 100 pages, depth 3

Settings are saved to your browser.

## Understanding Analysis Modes

### Quick Mode
- Faster analysis (~5-10 minutes)
- 20 pages maximum
- Depth of 2 links
- Best for initial research

### Thorough Mode
- Comprehensive analysis (~15-30 minutes)
- 100 pages maximum
- Depth of 3 links
- Best for detailed research

## Best Practices

### URL Tips
- Use the main company website (not social media)
- Include `https://` (added automatically if missing)
- Avoid URL parameters or tracking codes

### Getting Better Results
- Use **Thorough** mode for important prospects
- Enable LinkedIn following for team information
- Check the Pages tab to see what was crawled
- Re-scan periodically for updates

### Troubleshooting

**Analysis stuck on "Crawling"**
- Some sites block crawlers
- Try a shorter time limit
- Check if site has aggressive bot protection

**Few entities extracted**
- Site may have minimal content
- Try enabling external links
- Check if site is mostly images/video

**High token usage**
- More pages = more tokens
- Use Quick mode to reduce costs
- Disable external link following

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `/` | Focus search |
| `Esc` | Close modal |
| `Tab` | Navigate between elements |

## Status Reference

| Status | Meaning |
|--------|---------|
| Pending | Queued, waiting to start |
| In Progress | Currently being analyzed |
| Completed | Analysis finished successfully |
| Failed | Analysis encountered an error |
| Paused | Analysis paused by user |
