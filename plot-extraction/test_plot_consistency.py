"""Test plot name consistency validation."""
from transform_logic import folder_to_plot_name, filename_to_plot_name, validate_plot_consistency

# Test case from the warning
folder_name = "A16c - 167 MW"
filename = "603E-LT Cable Routing-A16c-BL02-R0-08042025_DWGData.xlsx"

print("="*80)
print("TESTING PLOT NAME CONSISTENCY")
print("="*80)

print(f"\nFolder name: {folder_name}")
plot_from_folder = folder_to_plot_name(folder_name)
print(f"Plot from folder: {plot_from_folder}")

print(f"\nFilename: {filename}")
plot_from_filename = filename_to_plot_name(filename)
print(f"Plot from filename: {plot_from_filename}")

print(f"\nValidation result: {validate_plot_consistency(plot_from_folder, plot_from_filename)}")

print("\n" + "="*80)
print("TESTING ALL PLOTS")
print("="*80)

test_cases = [
    ("A16a - 50 MW", "603C-LT Cable Routing-A16a-BL01-R0-30032025_DWGData.xlsx"),
    ("A16b - 200 MW", "603D-LT Cable Routing-A16b-BL01-R0-03042025_DWGData.xlsx"),
    ("A16c - 167 MW", "603E-LT Cable Routing-A16c-BL02-R0-08042025_DWGData.xlsx"),
    ("A16d - 333 MW", "603F-LT Cable Routing-A16d-BL01-R0-24042025_DWGData.xlsx"),
]

for folder, file in test_cases:
    folder_plot = folder_to_plot_name(folder)
    file_plot = filename_to_plot_name(file)
    is_valid = validate_plot_consistency(folder_plot, file_plot)
    
    status = "✅" if is_valid else "❌"
    print(f"\n{status} Folder: {folder}")
    print(f"   → {folder_plot}")
    print(f"   File: {file}")
    print(f"   → {file_plot}")
    print(f"   Match: {is_valid}")
