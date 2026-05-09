# # MARTA Service Performance Analysis
# ### Analyzing Scheduled Service Quality Across Atlanta's Transit Network
# 
# **Author:** Aidan Moran  
# **Date:** May 2026  
# **Data Source:** [MARTA GTFS Static Feed](https://itsmarta.com/app-developer-resources.aspx) & [MARTA KPI Dashboard](https://itsmarta.com/kpihome.aspx)  
# 
# ---
# 
# ## Project Overview
# 
# This analysis examines MARTA's service performance through two lenses:
# 
# 1. **Scheduled Service Analysis** — Using GTFS (General Transit Feed Specification) data to evaluate headways, service spans, route coverage, and service frequency across bus and rail modes.
# 2. **Published KPI Benchmarking** — Contextualizing schedule-based findings with MARTA's official Key Performance Indicators (on-time performance, missed trip rates, reliability metrics).
# 
# ### Key Questions
# - How does scheduled service frequency vary across routes and time of day?
# - Which routes have the longest and shortest headways?
# - How does bus service compare to rail in terms of coverage and frequency?
# - Where are the biggest gaps between MARTA's service targets and actual performance?
# - What does MARTA's service footprint look like geographically?

# ## 1. Setup & Imports

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import requests
import zipfile
import io
import os
import warnings

warnings.filterwarnings('ignore')

# Style configuration
plt.rcParams.update({
    'figure.figsize': (12, 6),
    'figure.dpi': 100,
    'font.size': 11,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'axes.spines.top': False,
    'axes.spines.right': False,
})

# MARTA brand-inspired palette
MARTA_COLORS = {
    'gold': '#D4A843',
    'red': '#CE3827',
    'green': '#009B3A',
    'blue': '#0074C8',
    'dark': '#1a1a2e',
    'gray': '#6c757d',
    'light_gray': '#f0f0f0',
    'orange': '#F18F01',
}

RAIL_COLORS = {
    'RED': MARTA_COLORS['red'],
    'GOLD': MARTA_COLORS['gold'],
    'GREEN': MARTA_COLORS['green'],
    'BLUE': MARTA_COLORS['blue'],
}

print('Setup complete. Ready to load MARTA data.')

# ## 2. Data Acquisition
# 
# MARTA publishes its schedule data in [GTFS format](https://gtfs.org/), the industry standard for transit feeds. The static feed includes:
# - **routes.txt** — Route definitions (name, type, color)
# - **trips.txt** — Individual trips on each route
# - **stop_times.txt** — Arrival/departure times at each stop for every trip
# - **stops.txt** — Stop locations (lat/lon, name)
# - **calendar.txt** — Service schedules (which days each service pattern runs)
# - **shapes.txt** — Geographic path of each route

# Download and extract MARTA GTFS feed
# Primary: MARTA direct, Fallback: Mobility Database mirror
GTFS_URLS = [
    'https://itsmarta.com/google_transit_feed/google_transit.zip',
    'https://files.mobilitydatabase.org/mdb-368/mdb-368-202604190110/mdb-368-202604190110.zip',
]
DATA_DIR = os.path.join('..', 'data', 'raw', 'marta_gtfs')

os.makedirs(DATA_DIR, exist_ok=True)

# Check if already downloaded
if not os.path.exists(os.path.join(DATA_DIR, 'routes.txt')):
    print('Downloading MARTA GTFS feed...')
    response = None
    for url in GTFS_URLS:
        try:
            print(f'  Trying {url[:60]}...')
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            print(f'  Success!')
            break
        except Exception as e:
            print(f'  Failed: {e}')
            response = None
    if response is None:
        raise RuntimeError('Could not download GTFS data from any source')
    
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        zf.extractall(DATA_DIR)
    print(f'Extracted {len(os.listdir(DATA_DIR))} files to {DATA_DIR}')
else:
    print(f'GTFS data already exists at {DATA_DIR}')

print('\nFiles in GTFS feed:')
for f in sorted(os.listdir(DATA_DIR)):
    size = os.path.getsize(os.path.join(DATA_DIR, f))
    print(f'  {f:30s} {size:>10,} bytes')

# ## 3. Data Loading & Exploration

# Load core GTFS tables
routes = pd.read_csv(os.path.join(DATA_DIR, 'routes.txt'))
trips = pd.read_csv(os.path.join(DATA_DIR, 'trips.txt'))
stop_times = pd.read_csv(os.path.join(DATA_DIR, 'stop_times.txt'), 
                         dtype={'stop_id': str})
stops = pd.read_csv(os.path.join(DATA_DIR, 'stops.txt'), 
                    dtype={'stop_id': str})
calendar = pd.read_csv(os.path.join(DATA_DIR, 'calendar.txt'))

print('=== MARTA GTFS Data Summary ===')
print(f'Routes:     {len(routes):>6,}')
print(f'Trips:      {len(trips):>6,}')
print(f'Stop Times: {len(stop_times):>6,}')
print(f'Stops:      {len(stops):>6,}')
print(f'Service IDs: {len(calendar):>5,}')

# Explore route types
# GTFS route_type: 0=Tram/Streetcar, 1=Subway/Metro, 2=Rail, 3=Bus
route_type_map = {0: 'Streetcar', 1: 'Heavy Rail', 2: 'Commuter Rail', 3: 'Bus'}
routes['mode'] = routes['route_type'].map(route_type_map)

print('=== Routes by Mode ===')
mode_counts = routes['mode'].value_counts()
for mode, count in mode_counts.items():
    print(f'  {mode:15s}: {count} routes')

print(f'\n=== Sample Routes ===')
display_cols = ['route_id', 'route_short_name', 'route_long_name', 'mode']
available_cols = [c for c in display_cols if c in routes.columns]
routes[available_cols].head(10)

# Explore calendar / service patterns
day_cols = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
available_day_cols = [c for c in day_cols if c in calendar.columns]

print('=== Service Patterns ===')
for _, row in calendar.iterrows():
    days_active = [d[:3].title() for d in available_day_cols if row.get(d, 0) == 1]
    sid = row.get('service_id', 'unknown')
    print(f"  {sid}: {', '.join(days_active) if days_active else 'No days marked'}")

# ## 4. Service Frequency Analysis
# 
# A key measure of transit quality is **headway** — the time between consecutive vehicles on a route. Lower headways mean shorter wait times and more convenient service. Industry standards suggest:
# - **< 10 min**: High-frequency ("show up and go")
# - **10-15 min**: Frequent
# - **15-30 min**: Moderate
# - **30-60 min**: Infrequent
# - **> 60 min**: Very infrequent

def parse_gtfs_time(time_str):
    """Parse GTFS time string (HH:MM:SS) to minutes since midnight.
    
    GTFS allows hours >= 24 for trips past midnight.
    """
    if pd.isna(time_str):
        return np.nan
    parts = str(time_str).strip().split(':')
    return int(parts[0]) * 60 + int(parts[1]) + int(parts[2]) / 60


def minutes_to_time_str(minutes):
    """Convert minutes since midnight to readable time string."""
    h = int(minutes // 60) % 24
    m = int(minutes % 60)
    ampm = 'AM' if h < 12 else 'PM'
    h_12 = h % 12 or 12
    return f'{h_12}:{m:02d} {ampm}'


# Parse departure times
stop_times['departure_min'] = stop_times['departure_time'].apply(parse_gtfs_time)
stop_times['hour'] = (stop_times['departure_min'] // 60).astype('Int64')

print('Time parsing complete.')
print(f'Departure time range: {stop_times["departure_min"].min():.0f} - {stop_times["departure_min"].max():.0f} minutes')

# Identify the primary weekday service_id
weekday_services = calendar[
    (calendar.get('monday', 0) == 1) & 
    (calendar.get('tuesday', 0) == 1) & 
    (calendar.get('wednesday', 0) == 1) & 
    (calendar.get('thursday', 0) == 1) & 
    (calendar.get('friday', 0) == 1)
]['service_id'].tolist()

weekend_services = calendar[
    (calendar.get('saturday', 0) == 1) | 
    (calendar.get('sunday', 0) == 1)
]['service_id'].tolist()

print(f'Weekday service IDs: {weekday_services}')
print(f'Weekend service IDs: {weekend_services}')

# Filter trips to weekday service
weekday_trips = trips[trips['service_id'].isin(weekday_services)]
print(f'\nWeekday trips: {len(weekday_trips):,}')
print(f'Total trips:   {len(trips):,}')

# Compute headways: time between consecutive departures at each route's first stop
# For each trip, get the first stop departure (stop_sequence == 1 or min)

# Merge trips with routes to get mode info
trips_routes = weekday_trips.merge(routes[['route_id', 'route_short_name', 'route_long_name', 'mode']], 
                                    on='route_id', how='left')

# Get first stop time for each trip
first_stops = stop_times.sort_values('stop_sequence').groupby('trip_id').first().reset_index()
first_stops = first_stops[['trip_id', 'departure_min', 'hour']]

# Merge with trip/route info
trip_departures = trips_routes.merge(first_stops, on='trip_id', how='inner')

# For each route + direction, sort by departure time and compute headway
direction_col = 'direction_id' if 'direction_id' in trip_departures.columns else None
group_cols = ['route_id', 'route_short_name', 'mode']
if direction_col:
    group_cols.append(direction_col)

headway_records = []
for name, group in trip_departures.groupby(group_cols):
    sorted_deps = group.sort_values('departure_min')['departure_min'].values
    if len(sorted_deps) > 1:
        headways = np.diff(sorted_deps)
        headways = headways[(headways > 0) & (headways < 180)]  # filter unreasonable values
        if len(headways) > 0:
            record = {
                'route_id': name[0],
                'route_short_name': name[1],
                'mode': name[2],
                'avg_headway': np.mean(headways),
                'median_headway': np.median(headways),
                'min_headway': np.min(headways),
                'max_headway': np.max(headways),
                'num_trips': len(sorted_deps),
                'first_departure': sorted_deps[0],
                'last_departure': sorted_deps[-1],
                'service_span_hrs': (sorted_deps[-1] - sorted_deps[0]) / 60,
            }
            if direction_col:
                record['direction_id'] = name[3]
            headway_records.append(record)

headways_df = pd.DataFrame(headway_records)

# Aggregate across directions (average both directions)
route_headways = headways_df.groupby(['route_id', 'route_short_name', 'mode']).agg({
    'avg_headway': 'mean',
    'median_headway': 'mean',
    'min_headway': 'min',
    'max_headway': 'max',
    'num_trips': 'sum',
    'service_span_hrs': 'mean',
}).reset_index()

print(f'Computed headways for {len(route_headways)} routes')
print(f'\n=== Headway Summary by Mode ===')
for mode in route_headways['mode'].unique():
    subset = route_headways[route_headways['mode'] == mode]
    print(f'\n  {mode} ({len(subset)} routes):')
    print(f'    Avg headway:  {subset["avg_headway"].mean():.1f} min')
    print(f'    Median:       {subset["median_headway"].mean():.1f} min')
    print(f'    Range:        {subset["min_headway"].min():.0f} - {subset["max_headway"].max():.0f} min')
    print(f'    Avg span:     {subset["service_span_hrs"].mean():.1f} hrs')

# ### 4.1 Headway Distribution by Mode

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Left: Histogram of average headways
bus_headways = route_headways[route_headways['mode'] == 'Bus']['avg_headway']
rail_headways = route_headways[route_headways['mode'].isin(['Heavy Rail', 'Streetcar'])]['avg_headway']

axes[0].hist(bus_headways, bins=20, color=MARTA_COLORS['blue'], alpha=0.7, 
             edgecolor='white', label='Bus')
if len(rail_headways) > 0:
    axes[0].hist(rail_headways, bins=10, color=MARTA_COLORS['gold'], alpha=0.7, 
                 edgecolor='white', label='Rail/Streetcar')

# Add frequency threshold lines
for threshold, label, style in [(10, 'High Freq', '--'), (15, 'Frequent', ':'), (30, 'Moderate', '-.')]: 
    axes[0].axvline(threshold, color=MARTA_COLORS['gray'], linestyle=style, alpha=0.6)
    axes[0].text(threshold + 0.5, axes[0].get_ylim()[1] * 0.9, label, 
                fontsize=8, color=MARTA_COLORS['gray'])

axes[0].set_xlabel('Average Headway (minutes)')
axes[0].set_ylabel('Number of Routes')
axes[0].set_title('Distribution of Average Weekday Headways')
axes[0].legend()

# Right: Box plot by mode
modes_present = route_headways['mode'].unique()
box_data = [route_headways[route_headways['mode'] == m]['avg_headway'].values 
            for m in modes_present]
mode_colors = [MARTA_COLORS.get(m.lower().replace(' ', '_'), MARTA_COLORS['blue']) 
               for m in modes_present]

bp = axes[1].boxplot(box_data, labels=modes_present, patch_artist=True, 
                     widths=0.5, medianprops={'color': 'black', 'linewidth': 2})
palette = [MARTA_COLORS['blue'], MARTA_COLORS['gold'], MARTA_COLORS['orange']]
for patch, color in zip(bp['boxes'], palette[:len(bp['boxes'])]):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)

axes[1].set_ylabel('Average Headway (minutes)')
axes[1].set_title('Headway Comparison by Mode')
axes[1].axhline(15, color=MARTA_COLORS['green'], linestyle='--', alpha=0.5, label='Frequent threshold (15 min)')
axes[1].legend(fontsize=9)

plt.suptitle('MARTA Weekday Service Frequency', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(os.path.join('..', 'assets', 'marta_headway_distribution.png'), 
            dpi=150, bbox_inches='tight', facecolor='white')
plt.show()

# ### 4.2 Best and Worst Service Frequencies

bus_routes = route_headways[route_headways['mode'] == 'Bus'].copy()
bus_routes['route_label'] = bus_routes['route_short_name'].astype(str) 

# Top 15 most frequent bus routes
top_freq = bus_routes.nsmallest(15, 'avg_headway')
# Bottom 15 least frequent
bottom_freq = bus_routes.nlargest(15, 'avg_headway')

fig, axes = plt.subplots(1, 2, figsize=(16, 8))

# Most frequent
bars1 = axes[0].barh(range(len(top_freq)), top_freq['avg_headway'], 
                      color=MARTA_COLORS['green'], alpha=0.8, edgecolor='white')
axes[0].set_yticks(range(len(top_freq)))
axes[0].set_yticklabels(top_freq['route_label'])
axes[0].set_xlabel('Average Headway (minutes)')
axes[0].set_title('Most Frequent Bus Routes', fontweight='bold')
axes[0].invert_yaxis()
axes[0].axvline(15, color=MARTA_COLORS['gray'], linestyle='--', alpha=0.5)
for i, v in enumerate(top_freq['avg_headway']):
    axes[0].text(v + 0.3, i, f'{v:.0f} min', va='center', fontsize=9)

# Least frequent
bars2 = axes[1].barh(range(len(bottom_freq)), bottom_freq['avg_headway'], 
                      color=MARTA_COLORS['red'], alpha=0.7, edgecolor='white')
axes[1].set_yticks(range(len(bottom_freq)))
axes[1].set_yticklabels(bottom_freq['route_label'])
axes[1].set_xlabel('Average Headway (minutes)')
axes[1].set_title('Least Frequent Bus Routes', fontweight='bold')
axes[1].invert_yaxis()
for i, v in enumerate(bottom_freq['avg_headway']):
    axes[1].text(v + 0.5, i, f'{v:.0f} min', va='center', fontsize=9)

plt.suptitle('MARTA Bus Route Frequency Rankings (Weekday)', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(os.path.join('..', 'assets', 'marta_route_frequency_ranking.png'), 
            dpi=150, bbox_inches='tight', facecolor='white')
plt.show()

# ## 5. Service Span Analysis
# 
# Service span measures the hours of operation for each route — from first departure to last departure. Longer spans mean transit is available to more types of trips (early commuters, late-shift workers, nightlife).

# Service span visualization
bus_routes_sorted = bus_routes.sort_values('service_span_hrs', ascending=True)

fig, ax = plt.subplots(figsize=(12, 8))

# Categorize service span
def categorize_span(hrs):
    if hrs >= 18: return 'Full Day (18+ hrs)'
    elif hrs >= 14: return 'Extended (14-18 hrs)'
    elif hrs >= 10: return 'Standard (10-14 hrs)'
    else: return 'Limited (< 10 hrs)'

route_headways['span_category'] = route_headways['service_span_hrs'].apply(categorize_span)

span_counts = route_headways[route_headways['mode'] == 'Bus']['span_category'].value_counts()
span_order = ['Full Day (18+ hrs)', 'Extended (14-18 hrs)', 'Standard (10-14 hrs)', 'Limited (< 10 hrs)']
span_counts = span_counts.reindex([s for s in span_order if s in span_counts.index])

colors_span = [MARTA_COLORS['green'], MARTA_COLORS['blue'], MARTA_COLORS['orange'], MARTA_COLORS['red']]
bars = ax.bar(range(len(span_counts)), span_counts.values, 
              color=colors_span[:len(span_counts)], alpha=0.8, edgecolor='white', width=0.6)
ax.set_xticks(range(len(span_counts)))
ax.set_xticklabels(span_counts.index, rotation=15, ha='right')
ax.set_ylabel('Number of Bus Routes')
ax.set_title('MARTA Bus Routes by Service Span (Weekday)', fontsize=14, fontweight='bold')

for bar, count in zip(bars, span_counts.values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
            str(count), ha='center', fontweight='bold', fontsize=12)

plt.tight_layout()
plt.savefig(os.path.join('..', 'assets', 'marta_service_span.png'), 
            dpi=150, bbox_inches='tight', facecolor='white')
plt.show()

# ## 6. Hourly Service Patterns

# Count departures by hour for bus vs rail
weekday_stop_times = stop_times[stop_times['trip_id'].isin(weekday_trips['trip_id'])].copy()
weekday_st_routes = weekday_stop_times.merge(
    trips_routes[['trip_id', 'route_id', 'mode']], on='trip_id', how='left'
)

hourly_departures = weekday_st_routes.groupby(['hour', 'mode']).size().reset_index(name='departures')
hourly_departures = hourly_departures[hourly_departures['hour'].between(4, 25)]

fig, ax = plt.subplots(figsize=(14, 6))

for mode, color, marker in [('Bus', MARTA_COLORS['blue'], 'o'), 
                              ('Heavy Rail', MARTA_COLORS['gold'], 's'),
                              ('Streetcar', MARTA_COLORS['orange'], '^')]:
    subset = hourly_departures[hourly_departures['mode'] == mode]
    if len(subset) > 0:
        ax.plot(subset['hour'], subset['departures'], 
                marker=marker, linewidth=2.5, markersize=6,
                color=color, label=mode, alpha=0.9)

# Highlight peak periods
ax.axvspan(7, 9, alpha=0.08, color=MARTA_COLORS['red'], label='AM Peak (7-9)')
ax.axvspan(16, 19, alpha=0.08, color=MARTA_COLORS['orange'], label='PM Peak (4-7)')

ax.set_xlabel('Hour of Day')
ax.set_ylabel('Stop-Time Departures')
ax.set_title('MARTA Weekday Service Volume by Hour', fontsize=14, fontweight='bold')

# Format x-axis with AM/PM labels
hour_labels = {4:'4 AM', 6:'6 AM', 8:'8 AM', 10:'10 AM', 12:'12 PM', 
               14:'2 PM', 16:'4 PM', 18:'6 PM', 20:'8 PM', 22:'10 PM', 24:'12 AM'}
ax.set_xticks(list(hour_labels.keys()))
ax.set_xticklabels(list(hour_labels.values()), rotation=45)
ax.legend(loc='upper right')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: format(int(x), ',')))

plt.tight_layout()
plt.savefig(os.path.join('..', 'assets', 'marta_hourly_service.png'), 
            dpi=150, bbox_inches='tight', facecolor='white')
plt.show()

# ## 7. MARTA KPI Benchmarking
# 
# MARTA publishes monthly Key Performance Indicators on its [KPI Dashboard](https://itsmarta.com/kpihome.aspx). The data below was collected from the latest available reports (as of May 2026) and provides context for our schedule-based analysis.

# MARTA KPI data scraped from itsmarta.com/kpihome.aspx
kpi_data = pd.DataFrame([
    # Bus Service
    {'category': 'Bus', 'metric': 'On-Time Performance', 'value': 80.27, 'target': 78.5, 
     'unit': '%', 'period': 'Jan 2026', 'status': 'Meets'},
    {'category': 'Bus', 'metric': 'Missed Trip Rate', 'value': 6.96, 'target': 0.5, 
     'unit': '%', 'period': 'Feb 2026', 'status': 'Below'},
    {'category': 'Bus', 'metric': 'Mean Distance Between Failures', 'value': None, 'target': None, 
     'unit': 'miles', 'period': 'Latest', 'status': 'Below'},
    {'category': 'Bus', 'metric': 'Complaints per 100K Boardings', 'value': None, 'target': None, 
     'unit': 'count', 'period': 'Latest', 'status': 'Meets'},
    # Rail Service
    {'category': 'Rail', 'metric': 'On-Time Performance', 'value': 94.21, 'target': 95.0, 
     'unit': '%', 'period': 'Dec 2025', 'status': 'Below'},
    {'category': 'Rail', 'metric': 'Missed Trip Rate', 'value': None, 'target': None, 
     'unit': '%', 'period': 'Latest', 'status': 'Below'},
    {'category': 'Rail', 'metric': 'Mean Distance Between Failures', 'value': None, 'target': None, 
     'unit': 'miles', 'period': 'Latest', 'status': 'Below'},
    {'category': 'Rail', 'metric': 'Mean Dist Between Service Interruptions', 'value': None, 'target': None, 
     'unit': 'miles', 'period': 'Latest', 'status': 'Below'},
    {'category': 'Rail', 'metric': 'Complaints per 100K Boardings', 'value': None, 'target': None, 
     'unit': 'count', 'period': 'Latest', 'status': 'Exceeds'},
    # Streetcar
    {'category': 'Streetcar', 'metric': 'On-Time Performance', 'value': None, 'target': None, 
     'unit': '%', 'period': 'Latest', 'status': 'Exceeds'},
    {'category': 'Streetcar', 'metric': 'Missed Trip Rate', 'value': None, 'target': None, 
     'unit': '%', 'period': 'Latest', 'status': 'Below'},
    # Facilities
    {'category': 'Facilities', 'metric': 'Escalator Availability', 'value': None, 'target': None, 
     'unit': '%', 'period': 'Latest', 'status': 'Exceeds'},
    {'category': 'Facilities', 'metric': 'Elevator Availability', 'value': None, 'target': None, 
     'unit': '%', 'period': 'Latest', 'status': 'Exceeds'},
])

print('=== MARTA KPI Scorecard ===')
for cat in kpi_data['category'].unique():
    print(f'\n{cat}:')
    subset = kpi_data[kpi_data['category'] == cat]
    for _, row in subset.iterrows():
        status_icon = {'Exceeds': '🟢', 'Meets': '🟡', 'Below': '🔴'}.get(row['status'], '⚪')
        val_str = f"{row['value']}{row['unit']}" if pd.notna(row['value']) else 'N/A'
        tgt_str = f"(target: {row['target']}{row['unit']})" if pd.notna(row['target']) else ''
        print(f"  {status_icon} {row['metric']:45s} {val_str:>10s} {tgt_str}")

# Visualize the KPI status scorecard
kpi_with_values = kpi_data[kpi_data['value'].notna()].copy()

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# OTP comparison
otp_data = kpi_with_values[kpi_with_values['metric'] == 'On-Time Performance']
x = range(len(otp_data))
bar_colors = [MARTA_COLORS['blue'], MARTA_COLORS['gold']]

bars = axes[0].bar(x, otp_data['value'], color=bar_colors[:len(otp_data)], 
                    alpha=0.8, edgecolor='white', width=0.5)
for i, (_, row) in enumerate(otp_data.iterrows()):
    if pd.notna(row['target']):
        axes[0].hlines(row['target'], i-0.3, i+0.3, colors='black', 
                       linestyles='--', linewidth=2, label='Target' if i == 0 else None)
    axes[0].text(i, row['value'] + 0.5, f"{row['value']:.1f}%", 
                ha='center', fontweight='bold', fontsize=12)

axes[0].set_xticks(x)
axes[0].set_xticklabels(otp_data['category'])
axes[0].set_ylabel('On-Time Performance (%)')
axes[0].set_title('On-Time Performance vs. Target', fontweight='bold')
axes[0].set_ylim(0, 105)
axes[0].legend()

# Missed trip rate (bus) — dramatic gap
missed = kpi_with_values[kpi_with_values['metric'] == 'Missed Trip Rate']
if len(missed) > 0:
    row = missed.iloc[0]
    bars2 = axes[1].bar(['Actual', 'Target'], [row['value'], row['target']], 
                         color=[MARTA_COLORS['red'], MARTA_COLORS['green']], 
                         alpha=0.8, edgecolor='white', width=0.4)
    axes[1].text(0, row['value'] + 0.15, f"{row['value']}%", 
                ha='center', fontweight='bold', fontsize=14, color=MARTA_COLORS['red'])
    axes[1].text(1, row['target'] + 0.15, f"{row['target']}%", 
                ha='center', fontweight='bold', fontsize=14, color=MARTA_COLORS['green'])
    axes[1].set_ylabel('Missed Trip Rate (%)')
    axes[1].set_title('Bus Missed Trip Rate: Actual vs. Target', fontweight='bold')
    axes[1].annotate(f'{row["value"]/row["target"]:.0f}x over target', 
                     xy=(0.5, max(row['value'], row['target'])/2), 
                     fontsize=13, ha='center', color=MARTA_COLORS['red'],
                     fontweight='bold')

plt.suptitle('MARTA KPI Performance Snapshot', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(os.path.join('..', 'assets', 'marta_kpi_snapshot.png'), 
            dpi=150, bbox_inches='tight', facecolor='white')
plt.show()

# ## 8. Geographic Service Coverage
# 
# Using stop coordinates from the GTFS data, we can visualize MARTA's service footprint across Metro Atlanta.

try:
    import folium
    from folium.plugins import MarkerCluster
    
    # Get stops with their route info
    stop_routes = stop_times[['trip_id', 'stop_id']].drop_duplicates()
    stop_routes = stop_routes.merge(trips[['trip_id', 'route_id']], on='trip_id')
    stop_routes = stop_routes.merge(routes[['route_id', 'mode']], on='route_id')
    stop_routes = stop_routes[['stop_id', 'mode']].drop_duplicates()
    
    # Count how many routes serve each stop
    stop_route_counts = stop_times[['trip_id', 'stop_id']].drop_duplicates()\
        .merge(trips[['trip_id', 'route_id']], on='trip_id')\
        .groupby('stop_id')['route_id'].nunique().reset_index()\
        .rename(columns={'route_id': 'num_routes'})
    
    stops_geo = stops.merge(stop_route_counts, on='stop_id', how='left')
    stops_geo = stops_geo.merge(
        stop_routes.groupby('stop_id')['mode'].first().reset_index(), 
        on='stop_id', how='left'
    )
    stops_geo['num_routes'] = stops_geo['num_routes'].fillna(1)
    
    # Filter to valid coordinates
    stops_geo = stops_geo.dropna(subset=['stop_lat', 'stop_lon'])
    stops_geo = stops_geo[(stops_geo['stop_lat'] != 0) & (stops_geo['stop_lon'] != 0)]
    
    # Create map centered on Atlanta
    center_lat = stops_geo['stop_lat'].mean()
    center_lon = stops_geo['stop_lon'].mean()
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=11,
                   tiles='cartodbpositron')
    
    # Add rail stations as prominent markers
    rail_stops = stops_geo[stops_geo['mode'] == 'Heavy Rail']
    for _, stop in rail_stops.iterrows():
        folium.CircleMarker(
            location=[stop['stop_lat'], stop['stop_lon']],
            radius=8,
            popup=f"{stop.get('stop_name', 'Station')} ({stop['num_routes']:.0f} routes)",
            color=MARTA_COLORS['gold'],
            fill=True,
            fill_color=MARTA_COLORS['gold'],
            fill_opacity=0.8,
            weight=2,
        ).add_to(m)
    
    # Add bus stops with clustering
    bus_cluster = MarkerCluster(name='Bus Stops').add_to(m)
    bus_stops = stops_geo[stops_geo['mode'] == 'Bus']
    for _, stop in bus_stops.iterrows():
        folium.CircleMarker(
            location=[stop['stop_lat'], stop['stop_lon']],
            radius=3,
            popup=f"{stop.get('stop_name', 'Stop')} ({stop['num_routes']:.0f} routes)",
            color=MARTA_COLORS['blue'],
            fill=True,
            fill_color=MARTA_COLORS['blue'],
            fill_opacity=0.5,
            weight=1,
        ).add_to(bus_cluster)
    
    folium.LayerControl().add_to(m)
    
    # Save map
    map_path = os.path.join('..', 'maps', 'marta_service_coverage.html')
    os.makedirs(os.path.dirname(map_path), exist_ok=True)
    m.save(map_path)
    print(f'Interactive map saved to {map_path}')
    print(f'Rail stations mapped: {len(rail_stops)}')
    print(f'Bus stops mapped: {len(bus_stops)}')
    display(m)
    
except ImportError:
    print('Folium not installed. Install with: pip install folium')
    print('Skipping interactive map generation.')

# ## 9. Peak vs. Off-Peak Service Comparison

# Compute headways for peak (7-9, 16-19) vs off-peak hours
def compute_period_headways(trip_departures_df, hour_ranges, period_name):
    """Compute route-level headways for a given time period."""
    mask = pd.Series(False, index=trip_departures_df.index)
    for start_h, end_h in hour_ranges:
        mask |= trip_departures_df['hour'].between(start_h, end_h)
    
    period_deps = trip_departures_df[mask]
    records = []
    
    for (route_id, route_name, mode), group in period_deps.groupby(
            ['route_id', 'route_short_name', 'mode']):
        sorted_deps = group.sort_values('departure_min')['departure_min'].values
        if len(sorted_deps) > 1:
            headways = np.diff(sorted_deps)
            headways = headways[(headways > 0) & (headways < 180)]
            if len(headways) > 0:
                records.append({
                    'route_id': route_id,
                    'route_short_name': route_name,
                    'mode': mode,
                    'period': period_name,
                    'avg_headway': np.mean(headways),
                    'num_trips': len(sorted_deps),
                })
    return pd.DataFrame(records)

am_peak = compute_period_headways(trip_departures, [(7, 9)], 'AM Peak')
pm_peak = compute_period_headways(trip_departures, [(16, 19)], 'PM Peak')
midday = compute_period_headways(trip_departures, [(10, 15)], 'Midday')
evening = compute_period_headways(trip_departures, [(20, 23)], 'Evening')

period_headways = pd.concat([am_peak, pm_peak, midday, evening])

# Summary table
period_summary = period_headways[period_headways['mode'] == 'Bus'].groupby('period').agg(
    avg_headway=('avg_headway', 'mean'),
    median_headway=('avg_headway', 'median'),
    routes_served=('route_id', 'nunique'),
    total_trips=('num_trips', 'sum'),
).reindex(['AM Peak', 'Midday', 'PM Peak', 'Evening'])

print('=== Bus Service by Time Period (Weekday) ===')
print(period_summary.to_string())

# Visualization: peak vs off-peak
fig, ax = plt.subplots(figsize=(10, 6))

period_order = ['AM Peak', 'Midday', 'PM Peak', 'Evening']
colors_period = [MARTA_COLORS['red'], MARTA_COLORS['blue'], MARTA_COLORS['orange'], MARTA_COLORS['dark']]

bus_period = period_headways[period_headways['mode'] == 'Bus']

box_data_period = [bus_period[bus_period['period'] == p]['avg_headway'].values 
                   for p in period_order if p in bus_period['period'].values]
valid_periods = [p for p in period_order if p in bus_period['period'].values]

bp = ax.boxplot(box_data_period, labels=valid_periods, patch_artist=True,
                widths=0.5, medianprops={'color': 'black', 'linewidth': 2},
                showfliers=True, flierprops={'markersize': 3, 'alpha': 0.5})

for patch, color in zip(bp['boxes'], colors_period[:len(bp['boxes'])]):
    patch.set_facecolor(color)
    patch.set_alpha(0.6)

ax.axhline(15, color=MARTA_COLORS['green'], linestyle='--', alpha=0.5, 
           label='Frequent service threshold (15 min)')
ax.axhline(30, color=MARTA_COLORS['gray'], linestyle=':', alpha=0.5, 
           label='Moderate service threshold (30 min)')

ax.set_ylabel('Average Headway (minutes)')
ax.set_title('Bus Headway Distribution by Time Period (Weekday)', 
             fontsize=14, fontweight='bold')
ax.legend(loc='upper right', fontsize=9)

plt.tight_layout()
plt.savefig(os.path.join('..', 'assets', 'marta_peak_offpeak.png'), 
            dpi=150, bbox_inches='tight', facecolor='white')
plt.show()

# ## 10. System-Wide Summary Statistics

# Build a comprehensive summary table
summary_stats = []

for mode in route_headways['mode'].unique():
    subset = route_headways[route_headways['mode'] == mode]
    summary_stats.append({
        'Mode': mode,
        'Routes': len(subset),
        'Total Weekday Trips': subset['num_trips'].sum(),
        'Avg Headway (min)': round(subset['avg_headway'].mean(), 1),
        'Median Headway (min)': round(subset['median_headway'].mean(), 1),
        'Min Headway (min)': round(subset['min_headway'].min(), 0),
        'Max Headway (min)': round(subset['max_headway'].max(), 0),
        'Avg Service Span (hrs)': round(subset['service_span_hrs'].mean(), 1),
        'Routes < 15 min headway': (subset['avg_headway'] < 15).sum(),
        'Routes > 30 min headway': (subset['avg_headway'] > 30).sum(),
    })

summary_df = pd.DataFrame(summary_stats)
print('=== MARTA System-Wide Service Summary (Weekday) ===')
summary_df.set_index('Mode')

# ## 11. Key Findings & Insights
# 
# ### Schedule-Based Findings
# 
# 1. **Service frequency varies dramatically across bus routes.** The most frequent routes operate at headways under 15 minutes, while many routes run hourly or worse — a significant equity concern for riders dependent on infrequent routes.
# 
# 2. **Peak-hour service is measurably better than off-peak.** Headways during AM and PM peaks are noticeably shorter than midday and evening periods, though many routes still operate at 20-30+ minute headways even during rush hour.
# 
# 3. **Rail maintains consistently shorter headways than bus** across all time periods, reflecting the fixed-guideway advantage and MARTA's prioritization of rail service.
# 
# 4. **Service spans are generally adequate** — most bus routes operate 14+ hours on weekdays — but some peripheral routes have limited hours that may not serve shift workers.
# 
# ### KPI Performance Context
# 
# 5. **The 6.96% bus missed trip rate is alarming** — nearly 14x the 0.5% target. This means riders on routes with 30-minute scheduled headways may actually face 60+ minute waits when trips are cancelled, particularly on routes in South Atlanta and the western suburbs where cancellations are concentrated.
# 
# 6. **Bus OTP (80.27%) meets its target**, but the target itself (78.5%) is modest compared to industry benchmarks. Meanwhile, rail OTP (94.21%) narrowly missed its 95% target.
# 
# 7. **Reliability metrics (MDBF, MDBSI) are "Needs Improvement"** for both bus and rail, suggesting aging fleet and infrastructure challenges.
# 
# ### Implications
# 
# The combination of infrequent scheduled service on many routes and a high missed trip rate creates a compounding reliability problem: riders on low-frequency routes face the worst consequences of cancellations. MARTA's April 2026 NextGen Bus Network redesign aims to address some of these frequency issues, and future analysis comparing pre- and post-NextGen service levels would be valuable.
# 
# ---
# 
# ### Next Steps
# - **GTFS-Realtime analysis**: Use vehicle position and trip update feeds to measure actual vs. scheduled performance
# - **Pre/post NextGen comparison**: Analyze how the April 2026 bus network redesign changed frequencies
# - **Equity overlay**: Merge with Census ACS data to assess service quality vs. demographics
# - **Peer comparison**: Benchmark MARTA against similar-sized transit agencies using NTD data

# ---
# 
# ## Data Sources
# 
# - **MARTA GTFS Static Feed** — [itsmarta.com/app-developer-resources.aspx](https://itsmarta.com/app-developer-resources.aspx) (Effective Date: April 18, 2026)
# - **MARTA Key Performance Indicators** — [itsmarta.com/kpihome.aspx](https://itsmarta.com/kpihome.aspx)
# - **GTFS Specification** — [gtfs.org](https://gtfs.org/)
# 
# ## Tools Used
# 
# Python, Pandas, NumPy, Matplotlib, Seaborn, Folium
