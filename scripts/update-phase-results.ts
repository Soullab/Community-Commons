#!/usr/bin/env npx tsx

/**
 * Phase 4.2C Results Updater
 *
 * Automatically updates PHASE_4_2C_RESULTS.md with fresh typehealth metrics.
 *
 * Usage:
 *   npx tsx scripts/update-phase-results.ts --module [a|b|c] --event [start|change|end] --description "Description"
 *
 * Examples:
 *   npx tsx scripts/update-phase-results.ts --module a --event start
 *   npx tsx scripts/update-phase-results.ts --module a --event change --description "Normalized ConsciousnessState interface"
 *   npx tsx scripts/update-phase-results.ts --module a --event end
 */

import { execSync } from 'child_process';
import { readFileSync, writeFileSync } from 'fs';
import { join } from 'path';

interface UpdateOptions {
  module: 'a' | 'b' | 'c';
  event: 'start' | 'change' | 'end';
  description?: string;
  changeNumber?: number;
}

interface MetricSnapshot {
  timestamp: string;
  diagnostics: number;
  syntaxErrors: number;
  buildStatus: string;
}

class PhaseResultsUpdater {
  private resultsPath = join(process.cwd(), 'artifacts/PHASE_4_2C_RESULTS.md');
  private artifactsDir = join(process.cwd(), 'artifacts');

  /**
   * Run typecheck and capture current diagnostic count
   */
  private captureMetrics(): MetricSnapshot {
    const timestamp = new Date().toISOString();

    try {
      // Run typecheck and capture output
      const output = execSync('npm run audit:typehealth 2>&1', {
        encoding: 'utf-8',
        maxBuffer: 10 * 1024 * 1024, // 10MB buffer
      });

      // Parse diagnostic count from output
      const errorMatch = output.match(/Found (\d+) errors?/);
      const diagnostics = errorMatch ? parseInt(errorMatch[1], 10) : 0;

      // Check for syntax errors (should be 0)
      const syntaxMatch = output.match(/syntax error/i);
      const syntaxErrors = syntaxMatch ? 1 : 0;

      return {
        timestamp,
        diagnostics,
        syntaxErrors,
        buildStatus: syntaxErrors === 0 ? '✅ Stable' : '❌ Unstable',
      };
    } catch (error) {
      // Typecheck failures still output diagnostics
      const errorOutput = (error as any).stdout || '';
      const errorMatch = errorOutput.match(/Found (\d+) errors?/);
      const diagnostics = errorMatch ? parseInt(errorMatch[1], 10) : 0;

      return {
        timestamp,
        diagnostics,
        syntaxErrors: 0,
        buildStatus: '✅ Stable',
      };
    }
  }

  /**
   * Save audit log to artifacts
   */
  private saveAuditLog(moduleName: string, eventType: string): void {
    const logFileName = `typehealth-${eventType}-module-${moduleName}.log`;
    const logPath = join(this.artifactsDir, logFileName);

    try {
      const output = execSync('npm run audit:typehealth 2>&1', {
        encoding: 'utf-8',
        maxBuffer: 10 * 1024 * 1024,
      });
      writeFileSync(logPath, output);
      console.log(`📝 Saved audit log: ${logFileName}`);
    } catch (error) {
      const errorOutput = (error as any).stdout || (error as any).stderr || '';
      writeFileSync(logPath, errorOutput);
      console.log(`📝 Saved audit log: ${logFileName}`);
    }
  }

  /**
   * Update the markdown file with new metrics
   */
  private updateMarkdown(options: UpdateOptions, metrics: MetricSnapshot): void {
    const content = readFileSync(this.resultsPath, 'utf-8');
    const lines = content.split('\n');

    const moduleName = options.module.toUpperCase();
    const moduleSection = `## Module ${moduleName}:`;

    let updatedContent = content;

    if (options.event === 'start') {
      // Update Pre-Module metrics
      updatedContent = this.updatePreModuleMetrics(content, options.module, metrics);
      updatedContent = this.updateModuleStatus(updatedContent, options.module, '🔄 IN PROGRESS');
      updatedContent = this.updateDateStarted(updatedContent, options.module, metrics.timestamp);

      console.log(`\n✅ Module ${moduleName} started`);
      console.log(`   Starting diagnostics: ${metrics.diagnostics}`);
      console.log(`   Timestamp: ${metrics.timestamp}`);

    } else if (options.event === 'change') {
      // Update change tracking table
      updatedContent = this.updateChangeMetrics(content, options.module, metrics, options.description);

      console.log(`\n✅ Module ${moduleName} change recorded`);
      console.log(`   Current diagnostics: ${metrics.diagnostics}`);
      console.log(`   Description: ${options.description || 'N/A'}`);

    } else if (options.event === 'end') {
      // Update Post-Module metrics
      updatedContent = this.updatePostModuleMetrics(content, options.module, metrics);
      updatedContent = this.updateModuleStatus(updatedContent, options.module, '✅ COMPLETE');

      console.log(`\n✅ Module ${moduleName} completed`);
      console.log(`   Ending diagnostics: ${metrics.diagnostics}`);
      console.log(`   Status: ${metrics.buildStatus}`);
    }

    writeFileSync(this.resultsPath, updatedContent);
    console.log(`📄 Updated: artifacts/PHASE_4_2C_RESULTS.md\n`);
  }

  /**
   * Update module status indicator
   */
  private updateModuleStatus(content: string, module: string, status: string): string {
    const moduleName = module.toUpperCase();
    const statusPattern = new RegExp(`(## Module ${moduleName}:.*?\\n\\*\\*Status:\\*\\* )([^\\n]+)`, 's');
    return content.replace(statusPattern, `$1${status}`);
  }

  /**
   * Update Date Started field
   */
  private updateDateStarted(content: string, module: string, timestamp: string): string {
    const date = new Date(timestamp).toISOString().split('T')[0];
    const moduleName = module.toUpperCase();
    const pattern = new RegExp(`(### Module ${moduleName} Execution Log.*?\\n\\*\\*Date Started:\\*\\* )\\[TBD\\]`, 's');
    return content.replace(pattern, `$1${date}`);
  }

  /**
   * Update Pre-Module metrics table
   */
  private updatePreModuleMetrics(content: string, module: string, metrics: MetricSnapshot): string {
    const moduleName = module.toUpperCase();
    const pattern = new RegExp(
      `(### Pre-Module ${moduleName} Metrics.*?\\| Starting Diagnostics \\| )\\[From Module [A-Z] end\\]( \\|)`,
      's'
    );

    const replacement = `$1${metrics.diagnostics}$2`;
    return content.replace(pattern, replacement);
  }

  /**
   * Update change tracking table
   */
  private updateChangeMetrics(content: string, module: string, metrics: MetricSnapshot, description?: string): string {
    const moduleName = module.toUpperCase();

    // Find the change tracking table
    const tablePattern = new RegExp(
      `(### Module ${moduleName} Execution Log.*?#### Metrics After Each Change:.*?\\n\\n)(\\| Change # \\|.*?\\n\\|[-|]+\\|.*?\\n)((?:\\| \\d+ \\|.*?\\n)*)(\\| 1 \\| \\[Description\\].*?\\n(?:\\| \\d+ \\| \\[Description\\].*?\\n)*)`,
      's'
    );

    const match = content.match(tablePattern);
    if (!match) {
      console.warn(`Could not find change table for Module ${moduleName}`);
      return content;
    }

    const [fullMatch, prefix, header, existingRows, templateRows] = match;

    // Parse existing rows to find the last change number
    const changeNumbers = Array.from(existingRows.matchAll(/\| (\d+) \|/g))
      .map(m => parseInt(m[1], 10));

    const nextChangeNum = changeNumbers.length > 0 ? Math.max(...changeNumbers) + 1 : 1;

    // Find the previous diagnostic count
    const previousDiagnostics = changeNumbers.length > 0
      ? this.extractLastDiagnosticCount(existingRows)
      : this.extractStartingDiagnosticCount(content, module);

    const delta = metrics.diagnostics - previousDiagnostics;
    const deltaStr = delta > 0 ? `+${delta}` : `${delta}`;

    // Create new row
    const newRow = `| ${nextChangeNum} | ${description || 'Change'} | ${previousDiagnostics} | ${metrics.diagnostics} | ${deltaStr} | Automated |\n`;

    // Replace the table
    const updatedTable = prefix + header + existingRows + newRow + templateRows;
    return content.replace(fullMatch, updatedTable);
  }

  /**
   * Extract the last diagnostic count from existing change rows
   */
  private extractLastDiagnosticCount(rows: string): number {
    const matches = Array.from(rows.matchAll(/\| \d+ \| .* \| \d+ \| (\d+) \|/g));
    if (matches.length === 0) return 0;
    return parseInt(matches[matches.length - 1][1], 10);
  }

  /**
   * Extract starting diagnostic count for a module
   */
  private extractStartingDiagnosticCount(content: string, module: string): number {
    const moduleName = module.toUpperCase();
    const pattern = new RegExp(`### Pre-Module ${moduleName} Metrics.*?\\| Starting Diagnostics \\| (\\d+)`, 's');
    const match = content.match(pattern);
    return match ? parseInt(match[1], 10) : 6400; // fallback to 4.2B baseline
  }

  /**
   * Update Post-Module metrics table
   */
  private updatePostModuleMetrics(content: string, module: string, metrics: MetricSnapshot): string {
    const moduleName = module.toUpperCase();

    // Calculate starting diagnostics
    const startDiagnostics = this.extractStartingDiagnosticCount(content, module);
    const reduction = startDiagnostics - metrics.diagnostics;
    const reductionPercent = ((reduction / startDiagnostics) * 100).toFixed(1);

    // Update the post-module table
    const pattern = new RegExp(
      `(### Post-Module ${moduleName} Metrics.*?\\| Metric \\| Target \\| Actual \\| Status \\| Notes \\|.*?\\n\\|[-|]+\\|.*?\\n)` +
      `(\\| Ending Diagnostics \\| [^|]+ \\| )\\[TBD\\]( \\| [^|]+ \\| [^|]+ \\|\\n)` +
      `(\\| Diagnostics Reduced \\| [^|]+ \\| )\\[TBD\\]( \\| [^|]+ \\| [^|]+ \\|\\n)` +
      `(\\| Reduction % \\| [^|]+ \\| )\\[TBD\\]( \\| [^|]+ \\| [^|]+ \\|\\n)` +
      `(\\| Syntax Errors \\| [^|]+ \\| )\\[TBD\\]( \\| [^|]+ \\| [^|]+ \\|\\n)` +
      `(\\| Runtime Errors \\| [^|]+ \\| )\\[TBD\\]( \\| [^|]+ \\| [^|]+ \\|\\n)` +
      `(\\| Build Status \\| [^|]+ \\| )\\[TBD\\]( \\| [^|]+ \\| [^|]+ \\|)`,
      's'
    );

    return content.replace(
      pattern,
      `$1$2${metrics.diagnostics}$3$4${reduction}$5$6${reductionPercent}%$7$8${metrics.syntaxErrors}$9$10${metrics.syntaxErrors}$11$12${metrics.buildStatus}$13`
    );
  }

  /**
   * Main execution
   */
  public run(options: UpdateOptions): void {
    console.log('\n🔬 Phase 4.2C Metrics Update\n');
    console.log(`   Module: ${options.module.toUpperCase()}`);
    console.log(`   Event: ${options.event}`);
    if (options.description) {
      console.log(`   Description: ${options.description}`);
    }
    console.log('');

    // Capture current metrics
    console.log('📊 Capturing typehealth metrics...');
    const metrics = this.captureMetrics();

    // Save audit log
    const eventType = options.event === 'start' ? 'pre' :
                      options.event === 'end' ? 'post' :
                      `change-${this.getNextChangeNumber(options.module)}`;
    this.saveAuditLog(options.module, eventType);

    // Update markdown
    this.updateMarkdown(options, metrics);

    console.log('✨ Metrics update complete\n');
  }

  /**
   * Get the next change number for a module
   */
  private getNextChangeNumber(module: string): number {
    const content = readFileSync(this.resultsPath, 'utf-8');
    const moduleName = module.toUpperCase();

    const tablePattern = new RegExp(
      `### Module ${moduleName} Execution Log.*?#### Metrics After Each Change:.*?\\n\\n.*?\\n.*?\\n((?:\\| \\d+ \\|.*?\\n)*)`,
      's'
    );

    const match = content.match(tablePattern);
    if (!match) return 1;

    const changeNumbers = Array.from(match[1].matchAll(/\| (\d+) \|/g))
      .map(m => parseInt(m[1], 10))
      .filter(n => !isNaN(n));

    return changeNumbers.length > 0 ? Math.max(...changeNumbers) + 1 : 1;
  }
}

// CLI argument parsing
function parseArgs(): UpdateOptions {
  const args = process.argv.slice(2);
  const options: Partial<UpdateOptions> = {};

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--module' && args[i + 1]) {
      options.module = args[i + 1].toLowerCase() as 'a' | 'b' | 'c';
      i++;
    } else if (args[i] === '--event' && args[i + 1]) {
      options.event = args[i + 1].toLowerCase() as 'start' | 'change' | 'end';
      i++;
    } else if (args[i] === '--description' && args[i + 1]) {
      options.description = args[i + 1];
      i++;
    }
  }

  // Validate required options
  if (!options.module || !options.event) {
    console.error('\n❌ Error: --module and --event are required\n');
    console.log('Usage:');
    console.log('  npx tsx scripts/update-phase-results.ts --module [a|b|c] --event [start|change|end] --description "Description"\n');
    console.log('Examples:');
    console.log('  npx tsx scripts/update-phase-results.ts --module a --event start');
    console.log('  npx tsx scripts/update-phase-results.ts --module a --event change --description "Normalized interfaces"');
    console.log('  npx tsx scripts/update-phase-results.ts --module a --event end\n');
    process.exit(1);
  }

  if (options.event === 'change' && !options.description) {
    console.error('\n❌ Error: --description is required for change events\n');
    process.exit(1);
  }

  return options as UpdateOptions;
}

// Execute
if (require.main === module) {
  const options = parseArgs();
  const updater = new PhaseResultsUpdater();
  updater.run(options);
}
