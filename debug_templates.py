#!/usr/bin/env python3
"""
Debug script to check template loading
"""
import pandas as pd

print("="*60)
print("Template Loading Debug Report")
print("="*60)

# Read templates
df = pd.read_csv('data/daily_task_templates.csv', sep='\t')

print(f"\nTotal templates loaded: {len(df)}")
print("\nAll templates:")
print(df[['name', 'is_default']])

print("\n" + "="*60)
print("Data Type Analysis:")
print("="*60)
print(f"is_default column type: {df['is_default'].dtype}")
print(f"Unique values in is_default: {df['is_default'].unique()}")
print(f"Value types: {[type(v).__name__ for v in df['is_default'].unique()]}")

print("\n" + "="*60)
print("Filtering Tests:")
print("="*60)

# Test different filtering methods
print("\n1. Filter with string 'true':")
result1 = df[df['is_default'] == 'true']
print(f"   Found {len(result1)} tasks: {list(result1['name'])}")

print("\n2. Filter with boolean True:")
result2 = df[df['is_default'] == True]
print(f"   Found {len(result2)} tasks: {list(result2['name'])}")

print("\n3. Filter with .astype(str).str.lower() == 'true' (FIXED METHOD):")
result3 = df[df['is_default'].astype(str).str.lower() == 'true']
print(f"   Found {len(result3)} tasks: {list(result3['name'])}")

print("\n" + "="*60)
print("Default vs Custom Tasks:")
print("="*60)

default_tasks = df[df['is_default'].astype(str).str.lower() == 'true']
custom_tasks = df[df['is_default'].astype(str).str.lower() == 'false']

print(f"\n✅ Default Tasks ({len(default_tasks)}):")
for _, task in default_tasks.iterrows():
    print(f"   • {task['name']} - UR:{task['duration_ur']}m SSR:{task['duration_ssr']}m SR:{task['duration_sr']}m")

print(f"\n✅ Custom Tasks ({len(custom_tasks)}):")
if custom_tasks.empty:
    print("   (none)")
else:
    for _, task in custom_tasks.iterrows():
        print(f"   • {task['name']} - UR:{task['duration_ur']}m SSR:{task['duration_ssr']}m SR:{task['duration_sr']}m")

print("\n" + "="*60)
print("✅ Debug complete!")
print("="*60)
