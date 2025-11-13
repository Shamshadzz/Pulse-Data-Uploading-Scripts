"""
Main CLI: orchestrates the full Excel → CSV pipeline.
"""
import sys
import json
from pathlib import Path

from src.staging_engine import StagingEngine
from src.append_writer import AppendOnlyWriter


def main():
    """Main entry point."""
    root = Path(__file__).parent.parent
    schema_path = root / 'build' / 'schema.json'
    mapping_path = root / 'config' / 'mapping_generated.yaml'
    workbook_path = root / 'Khavda Phase-3 Solar_Projects and SO Data (1).xlsx'
    data_dir = root / 'data'
    staging_dir = root / 'staging'
    backup_dir = root / 'backups'
    
    # Validation
    if not schema_path.exists():
        print("ERROR: Run 'python -m src.build_schema' first", file=sys.stderr)
        sys.exit(1)
    
    if not mapping_path.exists():
        print("ERROR: Run 'python -m src.generate_mapping' first", file=sys.stderr)
        sys.exit(1)
    
    if not workbook_path.exists():
        print(f"ERROR: Workbook not found: {workbook_path}", file=sys.stderr)
        sys.exit(1)
    
    # Check command
    if len(sys.argv) < 2:
        print("Usage: python -m src.main <command>")
        print("\nCommands:")
        print("  stage          - Transform and validate Excel data (dry-run)")
        print("  commit         - Stage and append to CSV (strict - aborts if ANY errors)")
        print("  commit-partial - Stage and append only error-free entities (skip entities with errors)")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    # Stage command (dry-run)
    if command == 'stage':
        print("=" * 60)
        print("DRY-RUN: STAGING ONLY (no changes to data/*.csv)")
        print("=" * 60)
        
        engine = StagingEngine(schema_path, mapping_path, workbook_path, data_dir, staging_dir)
        results = engine.stage_all()
        
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        
        total_valid = sum(r['valid_count'] for r in results.values())
        total_errors = sum(r['error_count'] for r in results.values())
        
        print(f"\nTotal valid rows: {total_valid}")
        print(f"Total errors: {total_errors}")
        
        if total_errors > 0:
            print("\nFirst 5 errors by entity:")
            for entity, result in results.items():
                if result['error_count'] > 0:
                    print(f"\n  {entity}: {result['error_count']} errors")
                    for err_rec in result['errors'][:5]:
                        print(f"    Row {err_rec['row_num']}: {', '.join(err_rec['errors'][:3])}")
        
        print(f"\nStaged files: {staging_dir}")
        print("\nRun 'python -m src.main commit' to append to data/*.csv")
    
    # Commit command (append to CSVs)
    elif command == 'commit':
        print("=" * 60)
        print("ATOMIC COMMIT: VALIDATION + APPEND")
        print("=" * 60)
        print("\nStep 1: Staging and validation...\n")
        
        engine = StagingEngine(schema_path, mapping_path, workbook_path, data_dir, staging_dir)
        staging_results = engine.stage_all()
        
        total_valid = sum(r['valid_count'] for r in staging_results.values())
        total_errors = sum(r['error_count'] for r in staging_results.values())
        
        print("\n" + "=" * 60)
        print("VALIDATION RESULTS")
        print("=" * 60)
        print(f"\nValid rows: {total_valid}")
        print(f"Errors: {total_errors}")
        
        # PRE-COMMIT VALIDATION: Abort if ANY errors exist
        if total_errors > 0:
            print("\n" + "=" * 60)
            print("❌ COMMIT ABORTED - VALIDATION FAILED")
            print("=" * 60)
            print(f"\nFound {total_errors} errors that must be fixed before commit.\n")
            
            # Show detailed error report
            print("Error breakdown by entity:")
            for entity, result in staging_results.items():
                if result['error_count'] > 0:
                    print(f"\n  {entity}: {result['error_count']} errors")
                    for err_rec in result['errors'][:5]:
                        row_num = err_rec.get('row_num', '?')
                        errors = err_rec.get('errors', [])
                        print(f"    Row {row_num}: {errors[0]}")
                        if len(errors) > 1:
                            for e in errors[1:3]:
                                print(f"              {e}")
                    if result['error_count'] > 5:
                        print(f"    ... and {result['error_count'] - 5} more errors")
            
            print(f"\n❌ NO FILES WERE MODIFIED")
            print(f"Fix errors in Excel and run 'stage' again to validate.")
            sys.exit(1)
        
        if total_valid == 0:
            print("\n❌ COMMIT ABORTED - No valid rows to append")
            sys.exit(1)
        
        # All validations passed - ready to commit
        print("\n✅ Validation passed - ready for atomic commit")
        print("\n" + "=" * 60)
        print("COMMIT PLAN")
        print("=" * 60)
        print(f"\nRows to append: {total_valid}")
        print(f"Entities to update:")
        for entity, result in staging_results.items():
            if result['valid_count'] > 0:
                csv_file = result.get('csv_file', f'CCTECH.DRS.ENTITIES-{entity}.csv')
                print(f"  • {entity}: +{result['valid_count']} rows → data/{csv_file}")
        print(f"\nBackups will be saved to: {backup_dir}")
        
        # Confirm
        response = input("\nProceed with atomic commit? [y/N]: ").strip().lower()
        if response != 'y':
            print("\n❌ Aborted by user - no files modified")
            sys.exit(0)
        
        print("\nStep 2: Creating backups and appending...\n")
        
        writer = AppendOnlyWriter(data_dir, staging_dir, backup_dir)
        append_results = writer.append_all(staging_results)
        
        print("\n" + "=" * 60)
        print("COMMIT SUMMARY")
        print("=" * 60)
        
        total_appended = sum(r['appended'] for r in append_results.values())
        total_failed = sum(1 for r in append_results.values() if r['error'])
        
        if total_failed > 0:
            print("\n❌ COMMIT FAILED - Rolling back changes")
            print("\nErrors encountered:")
            for entity, result in append_results.items():
                if result['error']:
                    print(f"  {entity}: {result['error']}")
            print(f"\n❌ Some files may have been modified - restore from {backup_dir}")
            sys.exit(1)
        
        print(f"\n✅ Successfully appended {total_appended} rows")
        print(f"\nUpdated entities:")
        for entity, result in append_results.items():
            if result['appended'] > 0:
                print(f"  ✓ {entity}: +{result['appended']} rows")
        
        print(f"\n✓ Backups saved to: {backup_dir}")
        print(f"✓ Data files updated in: {data_dir}")
        print("\n✅ COMMIT COMPLETED SUCCESSFULLY")
    
    # Commit-partial command (skip entities with errors)
    elif command == 'commit-partial':
        print("=" * 60)
        print("PARTIAL COMMIT: APPEND ONLY ERROR-FREE ENTITIES")
        print("=" * 60)
        print("\nStep 1: Staging and validation...\n")
        
        engine = StagingEngine(schema_path, mapping_path, workbook_path, data_dir, staging_dir)
        staging_results = engine.stage_all()
        
        total_valid = sum(r['valid_count'] for r in staging_results.values())
        total_errors = sum(r['error_count'] for r in staging_results.values())
        
        print("\n" + "=" * 60)
        print("VALIDATION RESULTS")
        print("=" * 60)
        print(f"\nValid rows: {total_valid}")
        print(f"Errors: {total_errors}")
        
        # Filter to error-free entities only
        clean_results = {
            entity: result 
            for entity, result in staging_results.items() 
            if result['error_count'] == 0 and result['valid_count'] > 0
        }
        
        skipped_results = {
            entity: result 
            for entity, result in staging_results.items() 
            if result['error_count'] > 0
        }
        
        if not clean_results:
            print("\n❌ COMMIT ABORTED - No error-free entities to append")
            sys.exit(1)
        
        clean_rows = sum(r['valid_count'] for r in clean_results.values())
        skipped_rows = sum(r['valid_count'] for r in skipped_results.values())
        error_rows = sum(r['error_count'] for r in skipped_results.values())
        
        print("\n" + "=" * 60)
        print("PARTIAL COMMIT PLAN")
        print("=" * 60)
        print(f"\n✅ Error-free entities ({len(clean_results)}): {clean_rows} rows")
        for entity, result in clean_results.items():
            csv_file = result.get('csv_file', f'CCTECH.DRS.ENTITIES-{entity}.csv')
            print(f"  ✓ {entity}: +{result['valid_count']} rows → data/{csv_file}")
        
        print(f"\n⚠️  Skipped entities ({len(skipped_results)}): {skipped_rows} valid + {error_rows} errors")
        for entity, result in skipped_results.items():
            print(f"  ⊗ {entity}: {result['valid_count']} valid, {result['error_count']} errors (SKIPPED)")
        
        print(f"\nBackups will be saved to: {backup_dir}")
        
        # Confirm
        response = input(f"\nAppend {clean_rows} rows from {len(clean_results)} entities? [y/N]: ").strip().lower()
        if response != 'y':
            print("\n❌ Aborted by user - no files modified")
            sys.exit(0)
        
        print("\nStep 2: Creating backups and appending...\n")
        
        writer = AppendOnlyWriter(data_dir, staging_dir, backup_dir)
        append_results = writer.append_all(clean_results)  # Only append clean entities
        
        print("\n" + "=" * 60)
        print("PARTIAL COMMIT SUMMARY")
        print("=" * 60)
        
        total_appended = sum(r['appended'] for r in append_results.values())
        total_failed = sum(1 for r in append_results.values() if r['error'])
        
        if total_failed > 0:
            print("\n❌ COMMIT FAILED - Errors during append")
            print("\nErrors encountered:")
            for entity, result in append_results.items():
                if result['error']:
                    print(f"  {entity}: {result['error']}")
            print(f"\n⚠️  Restore from backups: {backup_dir}")
            sys.exit(1)
        
        print(f"\n✅ Successfully appended {total_appended} rows")
        print(f"\nUpdated entities ({len(append_results)}):")
        for entity, result in append_results.items():
            if result['appended'] > 0:
                print(f"  ✓ {entity}: +{result['appended']} rows")
        
        if skipped_results:
            print(f"\n⚠️  Skipped {len(skipped_results)} entities with errors:")
            for entity, result in skipped_results.items():
                print(f"  ⊗ {entity}: {result['error_count']} errors (fix in Excel and re-run)")
        
        print(f"\n✓ Backups saved to: {backup_dir}")
        print(f"✓ Data files updated in: {data_dir}")
        print("\n✅ PARTIAL COMMIT COMPLETED")
    
    else:
        print(f"ERROR: Unknown command '{command}'", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
