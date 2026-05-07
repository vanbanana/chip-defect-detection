"""Test recipe loading."""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import Settings

print("Testing recipe loading...")
print("=" * 50)

settings = Settings()

# List files in recipe directory
recipe_dir = settings._recipe_dir
print(f"\nRecipe directory: {recipe_dir}")
print(f"Directory exists: {recipe_dir.exists()}")

print(f"\nFiles in directory:")
for f in recipe_dir.glob("*.json"):
    print(f"  - {f.name}")

# Try to load recipes
print(f"\nLoading recipes...")
recipes = settings.list_recipes()
print(f"Found {len(recipes)} recipes:")
for r in recipes:
    print(f"  - {r}")

# Get details
print(f"\nRecipe details:")
for name in recipes:
    recipe = settings.get_recipe(name)
    if recipe:
        print(f"\n  Name: {recipe.name}")
        print(f"  Algorithm: {recipe.algorithm}")
        print(f"  Description: {recipe.description}")
        print(f"  Parameters: {list(recipe.parameters.keys())}")
    else:
        print(f"  ERROR: Could not load {name}")
