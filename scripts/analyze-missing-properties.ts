#!/usr/bin/env npx tsx

/**
 * Interface Analysis Tool - Phase 4.2C Module A
 *
 * Analyzes TypeScript diagnostic logs to identify the most common missing
 * properties, providing data-driven targets for interface harmonization.
 *
 * Usage:
 *   npx tsx scripts/analyze-missing-properties.ts [log-file]
 *
 * Examples:
 *   npx tsx scripts/analyze-missing-properties.ts
 *   npx tsx scripts/analyze-missing-properties.ts artifacts/typecheck-full.log
 */

import { readFileSync, existsSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';

interface PropertyError {
  property: string;
  count: number;
  files: Set<string>;
  contexts: string[];
}

interface InterfaceCluster {
  inferredInterface: string;
  properties: string[];
  totalErrors: number;
  files: Set<string>;
}

class InterfaceAnalyzer {
  private logPath: string;
  private propertyErrors = new Map<string, PropertyError>();
  private typeObjectErrors = new Map<string, number>();

  constructor(logPath?: string) {
    // Default to latest typecheck log
    this.logPath = logPath || join(process.cwd(), 'artifacts/typehealth-phase4.2c-baseline.log');

    // Fallback to generating fresh log if file doesn't exist
    if (!existsSync(this.logPath)) {
      console.log('📊 No existing log found, generating fresh typecheck...\n');
      try {
        execSync('npm run audit:typehealth > artifacts/typecheck-analysis-temp.log 2>&1', {
          cwd: process.cwd(),
          encoding: 'utf-8',
        });
        this.logPath = join(process.cwd(), 'artifacts/typecheck-analysis-temp.log');
      } catch (error) {
        // Typecheck failures still produce output
        this.logPath = join(process.cwd(), 'artifacts/typecheck-analysis-temp.log');
      }
    }
  }

  /**
   * Parse the TypeScript diagnostic log
   */
  private parseLog(): void {
    const content = readFileSync(this.logPath, 'utf-8');
    const lines = content.split('\n');

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // Match: Property 'propertyName' does not exist on type 'TypeName'
      const propertyMatch = line.match(/error TS2339: Property '([^']+)' does not exist on type '([^']+)'/);
      if (propertyMatch) {
        const [, property, typeName] = propertyMatch;

        // Track property frequency
        if (!this.propertyErrors.has(property)) {
          this.propertyErrors.set(property, {
            property,
            count: 0,
            files: new Set(),
            contexts: [],
          });
        }
        const errorData = this.propertyErrors.get(property)!;
        errorData.count++;

        // Extract file path from previous line
        if (i > 0) {
          const fileMatch = lines[i - 1].match(/^([^(]+)\(/);
          if (fileMatch) {
            errorData.files.add(fileMatch[1]);
          }
        }

        // Track type context
        if (errorData.contexts.length < 5 && !errorData.contexts.includes(typeName)) {
          errorData.contexts.push(typeName);
        }

        // Track type object frequency
        this.typeObjectErrors.set(typeName, (this.typeObjectErrors.get(typeName) || 0) + 1);
      }
    }
  }

  /**
   * Cluster related properties into inferred interfaces
   */
  private clusterProperties(): InterfaceCluster[] {
    const clusters = new Map<string, InterfaceCluster>();

    // Group by primary type context
    for (const error of this.propertyErrors.values()) {
      const primaryType = error.contexts[0] || 'Unknown';

      if (!clusters.has(primaryType)) {
        clusters.set(primaryType, {
          inferredInterface: primaryType,
          properties: [],
          totalErrors: 0,
          files: new Set(),
        });
      }

      const cluster = clusters.get(primaryType)!;
      cluster.properties.push(error.property);
      cluster.totalErrors += error.count;
      error.files.forEach(file => cluster.files.add(file));
    }

    // Sort by total error count
    return Array.from(clusters.values()).sort((a, b) => b.totalErrors - a.totalErrors);
  }

  /**
   * Generate the analysis report
   */
  public analyze(): void {
    console.log('🔬 Phase 4.2C Module A - Interface Analysis\n');
    console.log(`📄 Analyzing: ${this.logPath}\n`);

    // Parse the log
    this.parseLog();

    if (this.propertyErrors.size === 0) {
      console.log('✅ No property errors found!\n');
      return;
    }

    // Top missing properties
    console.log('═══════════════════════════════════════════════════════════');
    console.log('📊 TOP MISSING PROPERTIES (Ranked by Frequency)');
    console.log('═══════════════════════════════════════════════════════════\n');

    const sortedProperties = Array.from(this.propertyErrors.values())
      .sort((a, b) => b.count - a.count)
      .slice(0, 25);

    sortedProperties.forEach((error, index) => {
      console.log(`${(index + 1).toString().padStart(2)}. ${error.property.padEnd(30)} ${error.count.toString().padStart(4)} errors`);
      console.log(`    Types: ${error.contexts.join(', ')}`);
      console.log(`    Files: ${error.files.size} affected\n`);
    });

    // Interface clusters
    console.log('═══════════════════════════════════════════════════════════');
    console.log('🏗️  INTERFACE CLUSTERS (Grouped by Type Context)');
    console.log('═══════════════════════════════════════════════════════════\n');

    const clusters = this.clusterProperties().slice(0, 10);

    clusters.forEach((cluster, index) => {
      console.log(`${(index + 1).toString().padStart(2)}. ${cluster.inferredInterface}`);
      console.log(`    Total Errors: ${cluster.totalErrors}`);
      console.log(`    Files: ${cluster.files.size} affected`);
      console.log(`    Missing Properties (${cluster.properties.length}):`);
      cluster.properties.slice(0, 10).forEach(prop => {
        console.log(`      - ${prop}`);
      });
      if (cluster.properties.length > 10) {
        console.log(`      ... and ${cluster.properties.length - 10} more`);
      }
      console.log('');
    });

    // Summary statistics
    console.log('═══════════════════════════════════════════════════════════');
    console.log('📈 SUMMARY STATISTICS');
    console.log('═══════════════════════════════════════════════════════════\n');

    const totalErrors = Array.from(this.propertyErrors.values()).reduce((sum, e) => sum + e.count, 0);
    const totalProperties = this.propertyErrors.size;
    const totalTypes = this.typeObjectErrors.size;

    console.log(`Total Property Errors:     ${totalErrors}`);
    console.log(`Unique Missing Properties: ${totalProperties}`);
    console.log(`Affected Type Contexts:    ${totalTypes}\n`);

    // Recommendations
    console.log('═══════════════════════════════════════════════════════════');
    console.log('💡 RECOMMENDED ACTIONS');
    console.log('═══════════════════════════════════════════════════════════\n');

    const top5Clusters = clusters.slice(0, 5);
    const estimatedReduction = top5Clusters.reduce((sum, c) => sum + c.totalErrors, 0);

    console.log('Start by harmonizing these interface clusters:\n');
    top5Clusters.forEach((cluster, index) => {
      console.log(`${index + 1}. Expand/Create: ${cluster.inferredInterface}`);
      console.log(`   → Would resolve ~${cluster.totalErrors} diagnostics\n`);
    });

    console.log(`Estimated total reduction: ~${estimatedReduction} diagnostics\n`);
    console.log('═══════════════════════════════════════════════════════════\n');
  }

  /**
   * Export data for programmatic use
   */
  public exportData(): {
    properties: PropertyError[];
    clusters: InterfaceCluster[];
    stats: { total: number; unique: number; types: number };
  } {
    this.parseLog();

    return {
      properties: Array.from(this.propertyErrors.values()).sort((a, b) => b.count - a.count),
      clusters: this.clusterProperties(),
      stats: {
        total: Array.from(this.propertyErrors.values()).reduce((sum, e) => sum + e.count, 0),
        unique: this.propertyErrors.size,
        types: this.typeObjectErrors.size,
      },
    };
  }
}

// CLI Execution
const logPath = process.argv[2];
const analyzer = new InterfaceAnalyzer(logPath);
analyzer.analyze();

export { InterfaceAnalyzer };
