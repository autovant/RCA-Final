import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(
  request: NextRequest,
  { params }: { params: { filename: string } }
) {
  try {
    const filename = params.filename;
    
    // Security: Only allow specific demo files
    const allowedFiles = [
      'demo-app-with-pii.log',
      'demo-blueprism-error.log',
      'demo-uipath-selector-error.log'
    ];
    
    if (!allowedFiles.includes(filename)) {
      return NextResponse.json(
        { error: 'File not found' },
        { status: 404 }
      );
    }
    
    // Path to sample-data directory (relative to project root)
    const sampleDataPath = path.join(process.cwd(), '..', 'sample-data', filename);
    
    // Check if file exists
    if (!fs.existsSync(sampleDataPath)) {
      return NextResponse.json(
        { error: 'File not found on server' },
        { status: 404 }
      );
    }
    
    // Read file content
    const fileContent = fs.readFileSync(sampleDataPath, 'utf-8');
    
    // Return file content as plain text
    return new NextResponse(fileContent, {
      status: 200,
      headers: {
        'Content-Type': 'text/plain',
      },
    });
  } catch (error) {
    console.error('Error serving demo file:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
