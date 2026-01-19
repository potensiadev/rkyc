const pptxgen = require('pptxgenjs');
const path = require('path');

// Set NODE_PATH to find global modules
const globalPath = require('child_process').execSync('npm root -g').toString().trim();
require('module').globalPaths.push(globalPath);

// Get html2pptx from skill directory
const html2pptx = require('C:/Users/USER/.claude/plugins/cache/anthropic-agent-skills/example-skills/00756142ab04/skills/pptx/scripts/html2pptx.js');

async function createPresentation() {
    const pptx = new pptxgen();

    // Presentation metadata
    pptx.layout = 'LAYOUT_16x9';
    pptx.title = 'rKYC System Architecture';
    pptx.author = 'rKYC Team';
    pptx.subject = 'Hackathon Demo Presentation';

    const slides = [
        'slide01_title.html',
        'slide02_problem.html',
        'slide03_solution.html',
        'slide04_architecture.html',
        'slide05_pipeline.html',
        'slide06_antihallucination.html',
        'slide07_signals.html',
        'slide08_database.html',
        'slide09_security.html',
        'slide10_demo.html'
    ];

    const workspaceDir = 'D:/rkyc/docs/ppt/workspace';

    for (let i = 0; i < slides.length; i++) {
        const htmlFile = path.join(workspaceDir, slides[i]);
        console.log(`Processing slide ${i + 1}: ${slides[i]}`);

        try {
            const { slide } = await html2pptx(htmlFile, pptx, { tmpDir: workspaceDir });
            console.log(`  - Slide ${i + 1} created successfully`);
        } catch (err) {
            console.error(`  - Error on slide ${i + 1}: ${err.message}`);
        }
    }

    // Save the presentation
    const outputPath = 'D:/rkyc/docs/ppt/rKYC_System_Architecture.pptx';
    await pptx.writeFile({ fileName: outputPath });
    console.log(`\nPresentation saved to: ${outputPath}`);
}

createPresentation().catch(console.error);
