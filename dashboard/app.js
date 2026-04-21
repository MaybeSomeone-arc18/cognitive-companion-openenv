document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const runBtn = document.getElementById('runBaselineBtn');
    const badge = document.querySelector('.status-badge');
    const valReward = document.getElementById('valReward');
    const valSteps = document.getElementById('valSteps');
    const valInterventions = document.getElementById('valInterventions');
    const valCompletion = document.getElementById('valCompletion');
    
    const frustrationVal = document.getElementById('frustrationVal');
    const frustrationFill = document.getElementById('frustrationFill');
    const storyContent = document.getElementById('storyContent');
    const timelineContainer = document.getElementById('timelineContainer');

    let isRunning = false;

    // Run Episode Button Click Handler
    runBtn.addEventListener('click', async () => {
        if (isRunning) return;
        isRunning = true;
        
        // Reset UI
        runBtn.disabled = true;
        runBtn.querySelector('.btn-text').textContent = 'Running...';
        badge.textContent = 'Live Episode';
        badge.classList.add('live');
        
        valReward.textContent = '0.00';
        valSteps.textContent = '0';
        valInterventions.textContent = '0';
        valCompletion.textContent = '0%';
        valInterventions.classList.remove('highlight');
        
        frustrationVal.textContent = '0%';
        frustrationFill.style.width = '0%';
        
        timelineContainer.innerHTML = '';
        // Clear any prior status; keep the default story text
        const statusEl = document.getElementById('story-status');
        if (statusEl) statusEl.textContent = '';

        try {
            const spinner = runBtn.querySelector('.btn-spinner');
            spinner.style.display = 'inline-block';
            
            // Fetch live simulation from the backend
            const response = await fetch('http://localhost:7860/baseline/run-once', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            
            const steps = data.steps;
            const summary = data.summary;

            let totalReward = 0;
            let interventions = 0;

            // Process step by step with delays for animation to show progression over time
            for (let i = 0; i < steps.length; i++) {
                await new Promise(resolve => setTimeout(resolve, 800)); // Delay for dramatic effect
                
                const step = steps[i];
                const stepNum = step.step;
                
                // Updating Metrics
                totalReward += step.reward;
                if (step.action === 'INTERVENE') {
                    interventions++;
                    valInterventions.classList.add('highlight');
                }

                animateValue(valReward, parseFloat(valReward.textContent), totalReward, 400, true);
                animateValue(valSteps, parseInt(valSteps.textContent), stepNum, 400);
                animateValue(valInterventions, parseInt(valInterventions.textContent), interventions, 400);
                
                // We use is_stuck visually for frustration
                const stuckPercent = step.is_stuck ? 80 + Math.random()*20 : (step.is_error_spiral ? 90 : Math.random()*30);
                frustrationVal.textContent = `${Math.round(stuckPercent)}%`;
                frustrationFill.style.width = `${stuckPercent}%`;
                if (stuckPercent > 70) {
                    frustrationFill.style.background = 'linear-gradient(90deg, #F59E0B, #EF4444)';
                } else {
                    frustrationFill.style.background = 'linear-gradient(90deg, var(--accent-cyan), #9D4EDD)';
                }

                // Trigger subtle pulse
                document.getElementById('pulseCard').classList.remove('data-update');
                void document.getElementById('pulseCard').offsetWidth; // trigger reflow
                document.getElementById('pulseCard').classList.add('data-update');

                // Create Timeline Entry
                addTimelineEntry(stepNum, step);
                timelineContainer.scrollTop = timelineContainer.scrollHeight;
            }

            // Sync final summary values exactly
            animateValue(valReward, parseFloat(valReward.textContent), summary.total_reward, 600, true);
            animateValue(valCompletion, parseFloat(valCompletion.textContent), summary.completion * 100, 600);
            
            // Dynamic Narrative
            generateNarrative(summary.total_reward, summary.interventions);

        } catch (error) {
            console.error("Backend fetch error:", error);
            const statusEl = document.getElementById('story-status');
            if (statusEl) {
                statusEl.textContent = 'Live baseline run temporarily unavailable. Try again in a bit.';
            }
        } finally {
            // Finalize Run
            isRunning = false;
            runBtn.disabled = false;
            runBtn.querySelector('.btn-text').textContent = 'Restart baseline';
            runBtn.querySelector('.btn-spinner').style.display = 'none';
            badge.textContent = 'Completed';
            badge.classList.remove('live');
        }
    });

    function addTimelineEntry(stepNum, step) {
        const item = document.createElement('div');
        item.className = 'timeline-item';
        
        let contentClass = 'timeline-content';
        let actDisplay = `<span style="opacity:0.7">Action:</span> <strong>${step.action}</strong>`;
        let errDisplay = step.is_error_spiral ? `<br><span style="color:var(--danger)">Error detected: Multiple sequential failures</span>` : '';
        let rwdDisplay = `<br><span style="opacity:0.5; font-size:0.8em">Reward: ${step.reward > 0 ? '+' : ''}${step.reward.toFixed(2)}</span>`;

        if (step.action === 'INTERVENE') {
            contentClass += ' action-intervene';
        } else if (step.is_error_spiral) {
            contentClass += ' error';
        }

        item.innerHTML = `
            <div class="timeline-step">STEP ${stepNum.toString().padStart(2, '0')}</div>
            <div class="${contentClass}">
                ${actDisplay}
                ${errDisplay}
                ${rwdDisplay}
            </div>
        `;
        timelineContainer.appendChild(item);
    }
    
    function animateValue(obj, start, end, duration, isFloat=false) {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            // easeOutQuad
            const ease = 1 - (1 - progress) * (1 - progress);
            const current = start + (end - start) * ease;
            
            if (obj === valCompletion) {
                obj.innerHTML = Math.round(current) + '%';
            } else {
                obj.innerHTML = isFloat ? current.toFixed(2) : Math.round(current);
            }
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    }

    function generateNarrative(rew, inter) {
        let text = '';
        if (inter > 0) {
            text = `The human hit a wall. We stayed quiet initially, but caught the downward spiral. Intervening at the right moment reset their frustration, letting them finish with a score of <strong>${rew.toFixed(2)}</strong>.`;
        } else {
            text = `Smooth sailing. The agent read the telemetry and knew exactly when to stay out of the way. Zero interruptions. Reward: <strong>${rew.toFixed(2)}</strong>.`;
        }
        storyContent.innerHTML = `<p>${text}</p>`;
    }
});
