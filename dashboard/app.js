document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements - safe querying
    const domElements = {
        runBtn: document.getElementById('runBaselineBtn'),
        badge: document.querySelector('.status-badge'),
        reward: document.getElementById('valReward'),
        steps: document.getElementById('valSteps'),
        interventions: document.getElementById('valInterventions'),
        completion: document.getElementById('valCompletion'),
        frustrationVal: document.getElementById('frustrationVal'),
        frustrationFill: document.getElementById('frustrationFill'),
        storyContent: document.getElementById('storyContent'),
        timelineContainer: document.getElementById('timelineContainer'),
        statusText: document.getElementById('story-status'),
        pulseCard: document.getElementById('pulseCard')
    };

    let isRunning = false;

    // Run Episode Button Click Handler
    if (domElements.runBtn) {
        domElements.runBtn.addEventListener('click', async () => {
            if (isRunning) return;
            isRunning = true;
            
            resetUI();

            try {
                const data = await fetchBaseline();
                
                let totalReward = 0;
                let interventionsCount = 0;

                const { steps, summary } = data;

                let accumulatedSteps = [];
                const baseTime = new Date();

                for (let i = 0; i < steps.length; i++) {
                    // Delay for dramatic effect
                    await new Promise(resolve => setTimeout(resolve, 800)); 
                    
                    const stepData = steps[i];
                    const stepNum = stepData.step;
                    
                    // Synthesize properties if missing
                    const stepTime = new Date(baseTime.getTime() + i * 60000); // add 1 min per step
                    stepData.timestamp = stepTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                    
                    const stuckPercent = stepData.is_stuck ? 80 + Math.random()*20 : (stepData.is_error_spiral ? 90 : Math.random()*30);
                    stepData.frustration = stuckPercent;

                    accumulatedSteps.push(stepData);

                    totalReward += stepData.reward;
                    if (stepData.action === 'INTERVENE') {
                        interventionsCount++;
                        if (domElements.interventions) {
                            domElements.interventions.classList.add('highlight');
                        }
                    }

                    // Determine Echo state dynamically based on current step
                    let echoState = 'RESTING';
                    if (stepData.action === 'INTERVENE') {
                        echoState = 'INTERVENING';
                    } else if (stepData.is_error_spiral || stuckPercent > 75) {
                        echoState = 'CONCERNED';
                    } else if (stuckPercent > 40) {
                        echoState = 'ATTENTIVE';
                    }
                    updateEchoState(echoState);
                    
                    drawTelemetryGraph(accumulatedSteps);

                    updateMetrics(totalReward, stepNum, interventionsCount, stepData);
                    renderTimeline(stepData, stepNum);
                }

                // Sync final summary values exactly
                if (domElements.reward) {
                    animateValue(domElements.reward, parseFloat(domElements.reward.textContent || '0'), summary.total_reward, 600, true);
                }
                if (domElements.completion) {
                    animateValue(domElements.completion, parseFloat(domElements.completion.textContent || '0'), summary.completion * 100, 600);
                }
                
                updateEchoState('RESTING');
                updateNarrative(summary.total_reward, summary.interventions);

            } catch (error) {
                console.error("Backend fetch error:", error);
                if (domElements.statusText) {
                    domElements.statusText.textContent = 'Live baseline run temporarily unavailable. Try again in a bit.';
                }
            } finally {
                finalizeRun();
            }
        });
    }

    function resetUI() {
        if (!domElements.runBtn) return;
        
        domElements.runBtn.disabled = true;
        
        const btnText = domElements.runBtn.querySelector('.btn-text');
        if (btnText) btnText.textContent = 'Running...';
        
        const spinner = domElements.runBtn.querySelector('.btn-spinner');
        if (spinner) spinner.style.display = 'inline-block';

        if (domElements.badge) {
            domElements.badge.textContent = 'Live Episode';
            domElements.badge.classList.add('live');
        }
        
        if (domElements.reward) domElements.reward.textContent = '0.00';
        if (domElements.steps) domElements.steps.textContent = '0';
        if (domElements.interventions) {
            domElements.interventions.textContent = '0';
            domElements.interventions.classList.remove('highlight');
        }
        if (domElements.completion) domElements.completion.textContent = '0%';
        
        if (domElements.frustrationVal) domElements.frustrationVal.textContent = '0%';
        if (domElements.frustrationFill) domElements.frustrationFill.style.width = '0%';
        
        if (domElements.timelineContainer) domElements.timelineContainer.innerHTML = '';
        if (domElements.statusText) domElements.statusText.textContent = '';
    }

    function finalizeRun() {
        isRunning = false;
        if (!domElements.runBtn) return;
        
        domElements.runBtn.disabled = false;
        
        const btnText = domElements.runBtn.querySelector('.btn-text');
        if (btnText) btnText.textContent = 'Restart baseline';
        
        const spinner = domElements.runBtn.querySelector('.btn-spinner');
        if (spinner) spinner.style.display = 'none';
        
        if (domElements.badge) {
            domElements.badge.textContent = 'Completed';
            domElements.badge.classList.remove('live');
        }
    }

    async function fetchBaseline() {
        const response = await fetch('/baseline/run-once', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    }

    function updateMetrics(totalReward, stepNum, interventionsCount, stepData) {
        if (domElements.reward) animateValue(domElements.reward, parseFloat(domElements.reward.textContent || '0'), totalReward, 400, true);
        if (domElements.steps) animateValue(domElements.steps, parseInt(domElements.steps.textContent || '0'), stepNum, 400);
        if (domElements.interventions) {
            animateValue(domElements.interventions, parseInt(domElements.interventions.textContent || '0'), interventionsCount, 400);
            if (stepData.action === 'INTERVENE') {
                domElements.interventions.classList.add('text-error', 'scale-110');
                setTimeout(() => domElements.interventions.classList.remove('scale-110'), 200);
            }
        }
        
        const stuckPercent = stepData.is_stuck ? 80 + Math.random()*20 : (stepData.is_error_spiral ? 90 : Math.random()*30);
        
        if (domElements.frustrationVal) domElements.frustrationVal.textContent = `${Math.round(stuckPercent)}%`;
        if (domElements.frustrationFill) {
            domElements.frustrationFill.style.width = `${stuckPercent}%`;
            if (stuckPercent > 70) {
                domElements.frustrationFill.style.background = 'var(--tw-colors-error)';
            } else {
                domElements.frustrationFill.style.background = 'var(--tw-colors-tertiary)';
            }
        }

        const compFill = document.getElementById('completionFill');
        if (compFill) {
            const completionPercent = (stepNum / 15) * 100; // approximation
            compFill.style.width = `${Math.min(completionPercent, 100)}%`;
        }

        if (domElements.pulseCard) {
            domElements.pulseCard.classList.remove('scale-105');
            void domElements.pulseCard.offsetWidth; // trigger reflow
            domElements.pulseCard.classList.add('scale-105', 'transition-transform');
            setTimeout(() => domElements.pulseCard.classList.remove('scale-105'), 200);
        }
    }

    function renderTimeline(stepData, stepNum) {
        if (!domElements.timelineContainer) return;

        // Clear placeholder text on first step
        if (stepNum === 1 && domElements.timelineContainer.querySelector('.text-outline-variant.italic')) {
            domElements.timelineContainer.innerHTML = '';
        }

        const item = document.createElement('div');
        item.className = 'relative';
        
        // Define color based on state
        let bulletColor = 'bg-background border-2 border-primary';
        let bgClass = 'bg-surface-container-lowest';
        let textClass = 'text-on-surface';

        let actDisplay = `<span class="opacity-70">Action:</span> <strong>${stepData.action}</strong>`;
        let errDisplay = stepData.is_error_spiral ? `<br><span class="text-error font-semibold">Error detected: Multiple sequential failures</span>` : '';
        let rwdDisplay = `<br><span class="opacity-50 text-sm">Reward: ${stepData.reward > 0 ? '+' : ''}${stepData.reward.toFixed(2)}</span>`;

        if (stepData.action === 'INTERVENE') {
            bulletColor = 'bg-primary';
            bgClass = 'bg-primary/10 border-primary';
        } else if (stepData.is_error_spiral) {
            bulletColor = 'bg-error';
            bgClass = 'bg-error/10 border-error';
        }

        const timeString = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

        item.innerHTML = `
            <div class="absolute -left-[31px] top-1 w-3 h-3 ${bulletColor} rounded-full"></div>
            <p class="text-label-sm text-outline-variant mb-1">STEP ${stepNum.toString().padStart(2, '0')} - ${timeString}</p>
            <div class="${bgClass} p-4 sketch-border relative">
                <p class="text-body-lg ${textClass} leading-relaxed">
                    ${actDisplay}
                    ${errDisplay}
                    ${rwdDisplay}
                </p>
            </div>
        `;
        domElements.timelineContainer.appendChild(item);
        
        // Find a scrollable parent (in our case the right panel or window)
        const scrollContainer = document.querySelector('main');
        if (scrollContainer) {
            scrollContainer.scrollTop = scrollContainer.scrollHeight;
        }
    }

    function updateNarrative(reward, inter) {
        if (!domElements.storyContent) return;
        
        let text = '';
        if (inter > 0) {
            text = `The human hit a wall. We stayed quiet initially, but caught the downward spiral. Intervening at the right moment reset their frustration, letting them finish with a score of <strong class="text-primary">${reward.toFixed(2)}</strong>.`;
        } else {
            text = `Smooth sailing. The agent read the telemetry and knew exactly when to stay out of the way. Zero interruptions. Reward: <strong class="text-primary">${reward.toFixed(2)}</strong>.`;
        }
        domElements.storyContent.innerHTML = `<p class="text-body-lg text-on-surface-variant leading-relaxed">${text}</p>`;
    }

    function animateValue(obj, start, end, duration, isFloat=false) {
        if (!obj) return;
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            // easeOutQuad
            const ease = 1 - (1 - progress) * (1 - progress);
            const current = start + (end - start) * ease;
            
            if (obj === domElements.completion) {
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

    function updateEchoState(state) {
        const bg = document.getElementById('echoBg');
        const pulse = document.getElementById('echoPulse');
        const dot = document.getElementById('echoStatusDot');
        const label = document.getElementById('echoStateLabel');
        const mouth = document.getElementById('echoMouth');
        const eyeL = document.getElementById('echoEyeL');
        const eyeR = document.getElementById('echoEyeR');
        const avatar = document.getElementById('echoAvatar');
        
        if (!bg || !label) return;

        // reset classes
        bg.className = 'relative w-12 h-12 rounded-full shadow-inner flex items-center justify-center overflow-hidden border transition-colors duration-500';
        pulse.className = 'absolute w-16 h-16 rounded-full animate-ping opacity-50 transition-colors duration-500';
        dot.className = 'absolute bottom-2 right-2 w-3.5 h-3.5 rounded-full border-2 transition-colors duration-300 shadow-sm border-surface-container-lowest';
        label.className = 'text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full transition-colors duration-300';
        avatar.className = 'w-full h-full transition-transform duration-1000 scale-90 text-primary';

        label.textContent = state;

        if (state === 'RESTING') {
            bg.classList.add('bg-primary-container', 'border-primary/20');
            pulse.classList.add('bg-primary/20');
            dot.classList.add('bg-primary');
            label.classList.add('bg-surface-variant', 'text-on-surface-variant');
            mouth.setAttribute('d', 'M 35,60 Q 50,70 65,60');
            eyeL.setAttribute('d', 'M 35,45 Q 35,35 40,40');
            eyeR.setAttribute('d', 'M 65,45 Q 65,35 60,40');
        } else if (state === 'ATTENTIVE') {
            bg.classList.add('bg-tertiary-container', 'border-tertiary/20');
            pulse.classList.add('bg-tertiary/20');
            dot.classList.add('bg-tertiary');
            label.classList.add('bg-tertiary-container', 'text-on-tertiary-container');
            avatar.classList.replace('text-primary', 'text-tertiary');
            mouth.setAttribute('d', 'M 40,65 Q 50,60 60,65');
            eyeL.setAttribute('d', 'M 35,40 A 5,5 0 1,1 35.1,40');
            eyeR.setAttribute('d', 'M 60,40 A 5,5 0 1,1 60.1,40');
        } else if (state === 'INTERVENING') {
            bg.classList.add('bg-primary', 'border-primary/50');
            pulse.classList.add('bg-primary');
            pulse.classList.replace('opacity-50', 'opacity-80');
            pulse.classList.replace('animate-ping', 'animate-pulse');
            dot.classList.add('bg-on-primary');
            label.classList.add('bg-primary', 'text-on-primary');
            avatar.classList.replace('text-primary', 'text-on-primary');
            mouth.setAttribute('d', 'M 40,65 Q 50,70 60,65');
            eyeL.setAttribute('d', 'M 35,42 Q 38,38 42,42');
            eyeR.setAttribute('d', 'M 65,42 Q 62,38 58,42');
        } else if (state === 'CONCERNED') {
            bg.classList.add('bg-error-container', 'border-error/20');
            pulse.classList.add('bg-error/20');
            dot.classList.add('bg-error');
            label.classList.add('bg-error-container', 'text-on-error-container');
            avatar.classList.replace('text-primary', 'text-error');
            mouth.setAttribute('d', 'M 35,65 Q 50,55 65,65');
            eyeL.setAttribute('d', 'M 35,38 L 45,42');
            eyeR.setAttribute('d', 'M 65,38 L 55,42');
        }
    }

    function drawTelemetryGraph(steps) {
        const svg = document.getElementById('telemetryGraphSvg');
        const container = document.getElementById('frustrationGraphContainer');
        const placeholder = document.getElementById('graphPlaceholder');
        
        if (!svg || !container) return;

        if (!steps || steps.length === 0) {
            if (placeholder) placeholder.style.display = 'flex';
            svg.innerHTML = '';
            return;
        }
        
        if (placeholder) placeholder.style.display = 'none';

        const viewBoxWidth = 1000;
        const viewBoxHeight = 400;
        svg.setAttribute('viewBox', `0 0 ${viewBoxWidth} ${viewBoxHeight}`);
        svg.innerHTML = ''; 

        for (let i = 0; i <= 4; i++) {
            const y = (i / 4) * viewBoxHeight;
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', '0');
            line.setAttribute('y1', y);
            line.setAttribute('x2', viewBoxWidth);
            line.setAttribute('y2', y);
            line.setAttribute('stroke', 'currentColor');
            line.setAttribute('stroke-opacity', '0.1');
            line.setAttribute('stroke-dasharray', '4 4');
            line.classList.add('text-outline-variant');
            svg.appendChild(line);
        }

        const points = steps.map((s, i) => {
            const x = (i / (Math.max(15, steps.length) - 1)) * viewBoxWidth;
            const y = viewBoxHeight - ((s.frustration || 0) / 100) * viewBoxHeight;
            return { x, y, data: s };
        });

        let pathD = `M 0,${viewBoxHeight} `;
        if (points.length > 0) {
            pathD += `L ${points[0].x},${points[0].y} `;
            for (let i = 1; i < points.length; i++) {
                const prev = points[i-1];
                const curr = points[i];
                const cx = (prev.x + curr.x) / 2;
                pathD += `C ${cx},${prev.y} ${cx},${curr.y} ${curr.x},${curr.y} `;
            }
            
            const linePath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            linePath.setAttribute('d', pathD.replace(`M 0,${viewBoxHeight} L `, 'M '));
            linePath.setAttribute('fill', 'none');
            linePath.setAttribute('stroke', 'var(--tw-colors-error)');
            linePath.setAttribute('stroke-width', '4');
            linePath.setAttribute('stroke-linecap', 'round');
            svg.appendChild(linePath);
            
            pathD += `L ${points[points.length-1].x},${viewBoxHeight} Z`;
            const areaPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            areaPath.setAttribute('d', pathD);
            areaPath.setAttribute('fill', 'var(--tw-colors-error)');
            areaPath.setAttribute('fill-opacity', '0.1');
            svg.insertBefore(areaPath, svg.firstChild);
        }

        points.forEach((p, i) => {
            const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            
            if (p.data.action === 'INTERVENE') {
                const marker = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
                marker.setAttribute('points', `${p.x},${p.y-10} ${p.x+10},${p.y} ${p.x},${p.y+10} ${p.x-10},${p.y}`);
                marker.setAttribute('fill', 'var(--tw-colors-primary)');
                group.appendChild(marker);
            } else {
                const marker = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                marker.setAttribute('cx', p.x);
                marker.setAttribute('cy', p.y);
                marker.setAttribute('r', '6');
                marker.setAttribute('fill', 'var(--tw-colors-surface)');
                marker.setAttribute('stroke', 'var(--tw-colors-error)');
                marker.setAttribute('stroke-width', '3');
                group.appendChild(marker);
            }

            const hitArea = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            hitArea.setAttribute('cx', p.x);
            hitArea.setAttribute('cy', p.y);
            hitArea.setAttribute('r', '25');
            hitArea.setAttribute('fill', 'transparent');
            hitArea.style.pointerEvents = 'all';
            hitArea.style.cursor = 'pointer';

            hitArea.addEventListener('mouseenter', (e) => showTooltip(e, p, container, viewBoxWidth, viewBoxHeight));
            hitArea.addEventListener('mouseleave', hideTooltip);

            group.appendChild(hitArea);
            svg.appendChild(group);
        });
    }

    const tooltip = document.getElementById('graphTooltip');
    function showTooltip(e, p, container, vbW, vbH) {
        if (!tooltip) return;
        
        const tTime = document.getElementById('tooltipTime');
        const tFrus = document.getElementById('tooltipFrustration');
        const tAct = document.getElementById('tooltipAction');
        const tRew = document.getElementById('tooltipReward');
        
        if (tTime) tTime.textContent = `${p.data.timestamp || 'Unknown Time'} — Step ${(p.data.step).toString().padStart(2, '0')}`;
        if (tFrus) tFrus.textContent = `${Math.round(p.data.frustration || 0)}%`;
        if (tAct) tAct.textContent = p.data.action || 'UNKNOWN';
        if (tRew) tRew.textContent = `${p.data.reward > 0 ? '+' : ''}${p.data.reward.toFixed(2)}`;

        const rect = container.getBoundingClientRect();
        const xRatio = p.x / vbW;
        const yRatio = p.y / vbH;
        
        const tooltipX = xRatio * rect.width;
        const tooltipY = yRatio * rect.height - 15; 

        tooltip.style.left = `${tooltipX}px`;
        tooltip.style.top = `${tooltipY}px`;
        tooltip.classList.remove('hidden', 'opacity-0');
    }

    function hideTooltip() {
        if (!tooltip) return;
        tooltip.classList.add('opacity-0');
        setTimeout(() => {
            if (tooltip.classList.contains('opacity-0')) {
                tooltip.classList.add('hidden');
            }
        }, 150);
    }

});

function initFrustrationTelemetryFromEpisodeLog() {
    const statusEl = document.getElementById('frustration-status');
    const graphContainer = document.getElementById('frustration-graph');
    const placeholder = document.getElementById('frustration-placeholder');
    const detailsEl = document.getElementById('frustration-details');
    const timelineContainer = document.getElementById('timelineContainer');
    
    if (!statusEl || !graphContainer || !placeholder || !detailsEl || !timelineContainer) {
        console.warn('Frustration Telemetry elements missing.');
        return;
    }

    // Parse steps from the DOM
    const stepEls = timelineContainer.querySelectorAll('.relative');
    const steps = [];
    let currentFrustration = 10;
    
    stepEls.forEach(el => {
        const headerEl = el.querySelector('p.text-label-sm');
        if (!headerEl) return;
        const headerMatch = headerEl.innerText.match(/STEP\s+(\d+)\s+-\s+(.+)/i);
        if (!headerMatch) return;
        
        const stepNum = parseInt(headerMatch[1], 10);
        const timestamp = headerMatch[2];
        
        const bodyEl = el.querySelector('p.text-body-lg');
        let action = "UNKNOWN";
        let reward = 0;
        if (bodyEl) {
            const bodyHtml = bodyEl.innerHTML;
            const actionMatch = bodyHtml.match(/Action:\s*<\/span>\s*<strong>(.*?)<\/strong>/);
            if (actionMatch) action = actionMatch[1];
            
            const rewardMatch = bodyHtml.match(/Reward:\s*([+-]?[\d.]+)/);
            if (rewardMatch) reward = parseFloat(rewardMatch[1]);
        }
        
        currentFrustration += (Math.random() * 20 - 10);
        if (action === 'INTERVENE') currentFrustration -= 30;
        currentFrustration = Math.max(0, Math.min(100, currentFrustration));
        
        steps.push({
            step: stepNum,
            timestamp: timestamp,
            action: action,
            reward: reward,
            frustration: currentFrustration
        });
    });

    if (steps.length === 0) {
        statusEl.textContent = 'Awaiting telemetry...';
        statusEl.className = 'text-xs font-bold uppercase tracking-widest px-2 py-1 rounded bg-surface-variant text-on-surface-variant';
        placeholder.style.display = 'block';
        detailsEl.innerHTML = 'No steps yet.';
        
        // Clear existing SVG if any
        const existingSvg = graphContainer.querySelector('svg');
        if (existingSvg) existingSvg.remove();
        const existingTt = graphContainer.querySelector('.shadow-lg');
        if (existingTt) existingTt.remove();
        
        updateEchoPanel(steps);
        return;
    }

    statusEl.textContent = 'Telemetry captured';
    statusEl.className = 'text-xs font-bold uppercase tracking-widest px-2 py-1 rounded text-primary bg-primary-container';
    placeholder.style.display = 'none';

    // Clear existing SVGs to redraw
    const existingSvg = graphContainer.querySelector('svg');
    if (existingSvg) existingSvg.remove();
    const existingTt = graphContainer.querySelector('.shadow-lg');
    if (existingTt) existingTt.remove();

    const svgNS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('class', 'absolute inset-0 w-full h-full pointer-events-none');
    svg.setAttribute('preserveAspectRatio', 'none');
    const vbW = 1000;
    const vbH = 400;
    svg.setAttribute('viewBox', `0 0 ${vbW} ${vbH}`);
    
    for (let i = 0; i <= 4; i++) {
        const y = (i / 4) * vbH;
        const line = document.createElementNS(svgNS, 'line');
        line.setAttribute('x1', '0');
        line.setAttribute('y1', y);
        line.setAttribute('x2', vbW);
        line.setAttribute('y2', y);
        line.setAttribute('stroke', 'currentColor');
        line.setAttribute('stroke-opacity', '0.1');
        line.setAttribute('stroke-dasharray', '4 4');
        line.setAttribute('class', 'text-outline-variant');
        svg.appendChild(line);
    }

    const pathGroup = document.createElementNS(svgNS, 'g');
    const markerGroup = document.createElementNS(svgNS, 'g');
    
    const polyline = document.createElementNS(svgNS, 'polyline');
    polyline.setAttribute('fill', 'none');
    polyline.setAttribute('stroke', 'var(--tw-colors-error, #ef4444)'); 
    polyline.setAttribute('stroke-width', '4');
    polyline.setAttribute('stroke-linecap', 'round');
    polyline.setAttribute('stroke-linejoin', 'round');
    polyline.style.transition = 'all 0.3s ease-out';
    pathGroup.appendChild(polyline);

    svg.appendChild(pathGroup);
    svg.appendChild(markerGroup);
    graphContainer.appendChild(svg);

    const tt = document.createElement('div');
    tt.className = 'absolute hidden opacity-0 transition-opacity bg-inverse-surface text-inverse-on-surface p-3 rounded-lg text-xs shadow-lg pointer-events-none z-50 min-w-[150px] transform -translate-x-1/2 -translate-y-[120%]';
    tt.innerHTML = `
        <div class="font-bold mb-1 border-b border-outline-variant/30 pb-1 uppercase tracking-wider text-inverse-primary" id="ftt-time"></div>
        <div class="flex justify-between gap-4 py-0.5"><span class="opacity-80">Frustration:</span><span class="font-semibold text-error" id="ftt-frus"></span></div>
        <div class="flex justify-between gap-4 py-0.5"><span class="opacity-80">Action:</span><span class="font-semibold" id="ftt-act"></span></div>
        <div class="flex justify-between gap-4 py-0.5"><span class="opacity-80">Reward:</span><span class="font-semibold text-inverse-primary" id="ftt-rew"></span></div>
        <div class="absolute bottom-0 left-1/2 transform -translate-x-1/2 translate-y-full w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[6px] border-t-inverse-surface"></div>
    `;
    graphContainer.appendChild(tt);

    function formatDetails(stepData) {
        if (!stepData) return "No steps yet.";
        return `
            <div class="flex w-full justify-between items-center">
                <span><span class="uppercase tracking-widest opacity-60 text-[10px] block mb-0.5">Time</span><span class="font-semibold">${stepData.timestamp}</span> <span class="opacity-50 mx-1">•</span> Step ${stepData.step}</span>
                <span class="text-center"><span class="uppercase tracking-widest opacity-60 text-[10px] block mb-0.5">Action</span><span class="font-semibold ${stepData.action === 'INTERVENE' ? 'text-primary' : ''}">${stepData.action}</span></span>
                <span class="text-right"><span class="uppercase tracking-widest opacity-60 text-[10px] block mb-0.5">Reward</span><span class="font-semibold ${stepData.reward >= 0 ? 'text-primary' : 'text-error'}">${stepData.reward >= 0 ? '+' : ''}${stepData.reward.toFixed(2)}</span></span>
            </div>
        `;
    }

    const maxSteps = Math.max(10, steps.length); 
    let pointsStr = '';
    markerGroup.innerHTML = '';
    
    steps.forEach((s, i) => {
        const x = (i / (maxSteps - 1)) * vbW;
        const y = vbH - ((s.frustration || 0) / 100) * vbH;
        
        pointsStr += `${x},${y} `;
        
        const group = document.createElementNS(svgNS, 'g');
        
        if (s.action === 'INTERVENE') {
            const marker = document.createElementNS(svgNS, 'polygon');
            marker.setAttribute('points', `${x},${y-12} ${x+12},${y} ${x},${y+12} ${x-12},${y}`);
            marker.setAttribute('fill', 'var(--tw-colors-primary, #10b981)');
            group.appendChild(marker);
        } else {
            const marker = document.createElementNS(svgNS, 'circle');
            marker.setAttribute('cx', x);
            marker.setAttribute('cy', y);
            marker.setAttribute('r', '5');
            marker.setAttribute('fill', 'var(--tw-colors-surface, #fff)');
            marker.setAttribute('stroke', 'var(--tw-colors-error, #ef4444)');
            marker.setAttribute('stroke-width', '3');
            group.appendChild(marker);
        }

        const hitArea = document.createElementNS(svgNS, 'circle');
        hitArea.setAttribute('cx', x);
        hitArea.setAttribute('cy', y);
        hitArea.setAttribute('r', '25');
        hitArea.setAttribute('fill', 'transparent');
        hitArea.style.pointerEvents = 'all';
        hitArea.style.cursor = 'pointer';

        hitArea.addEventListener('mouseenter', () => {
            const rect = graphContainer.getBoundingClientRect();
            const xRatio = x / vbW;
            const yRatio = y / vbH;
            const tooltipX = xRatio * rect.width;
            const tooltipY = yRatio * rect.height - 15;

            tt.style.left = `${tooltipX}px`;
            tt.style.top = `${tooltipY}px`;
            tt.classList.remove('hidden', 'opacity-0');
            
            tt.querySelector('#ftt-time').textContent = `${s.timestamp} — Step ${(s.step).toString().padStart(2, '0')}`;
            tt.querySelector('#ftt-frus').textContent = `${Math.round(s.frustration)}%`;
            tt.querySelector('#ftt-act').textContent = s.action;
            tt.querySelector('#ftt-rew').textContent = `${s.reward > 0 ? '+' : ''}${s.reward.toFixed(2)}`;
            
            detailsEl.innerHTML = formatDetails(s);
        });

        hitArea.addEventListener('mouseleave', () => {
            tt.classList.add('opacity-0');
            setTimeout(() => tt.classList.add('hidden'), 150);
            detailsEl.innerHTML = formatDetails(steps[steps.length - 1]);
        });

        group.appendChild(hitArea);
        markerGroup.appendChild(group);
    });

    polyline.setAttribute('points', pointsStr.trim());
    detailsEl.innerHTML = formatDetails(steps[steps.length - 1]);

    // Update Echo panel based on the current episode telemetry
    updateEchoPanel(steps);
}

function computeEchoMoment(steps, episodeStats) {
    if (!steps || steps.length === 0) {
        return {
            state: "Resting",
            summary: "Echo is resting. Awaiting telemetry."
        };
    }

    const interventionCount = episodeStats.interventions;
    const finalFrustration = episodeStats.finalFrustration;
    const completion = episodeStats.completion;

    const interventions = steps.filter(s => s.action === "INTERVENE");
    const interventionStep = interventions.length > 0 ? interventions[0].step : null;
    const avgFrustration = steps.reduce((acc, s) => acc + s.frustration, 0) / steps.length;

    if (interventionCount <= 1 && finalFrustration < 25 && completion >= 90) {
        return {
            state: "Resting",
            summary: "A very smooth session. Your signals were stable, so I kept my distance."
        };
    }

    if (interventionCount === 1 && interventionStep !== null) {
        const intFrus = interventions[0].frustration;
        if (finalFrustration < intFrus) {
            return {
                state: "Intervened",
                summary: `I noticed a spike near step ${interventionStep}. My single intervention seemed to help smooth things out.`
            };
        }
    }

    if (interventionCount >= 2 || avgFrustration >= 50) {
        return {
            state: "Concerned",
            summary: "This one was heavy. Your frustration stayed high and I had to step in more than once. Next run, I’ll be ready even earlier."
        };
    }

    // Fallback if none match perfectly
    return {
        state: "Resting",
        summary: "A very smooth session. Your signals were stable, so I kept my distance."
    };
}

function updateEchoPanel(steps) {
    const totalReward = parseFloat(document.getElementById('valReward')?.textContent || '0');
    const totalSteps = parseInt(document.getElementById('valSteps')?.textContent || '0', 10);
    const interventions = parseInt(document.getElementById('valInterventions')?.textContent || '0', 10);
    const compText = document.getElementById('valCompletion')?.textContent || '0%';
    const completion = parseFloat(compText.replace('%', ''));
    
    let finalFrustration = parseFloat((document.getElementById('frustrationVal')?.textContent || '0%').replace('%', ''));
    if (finalFrustration === 0 && steps.length > 0) {
        finalFrustration = steps[steps.length - 1].frustration;
    }

    const episodeStats = { totalReward, totalSteps, interventions, completion, finalFrustration };
    const mood = computeEchoMoment(steps, episodeStats);
    
    const labelEl = document.getElementById('echo-state-label');
    const summaryEl = document.getElementById('echo-summary');
    const indicatorEl = document.getElementById('echo-state-indicator');
    
    if (!labelEl || !summaryEl || !indicatorEl) return;
    
    labelEl.textContent = mood.state;
    summaryEl.textContent = mood.summary;
    
    indicatorEl.className = 'inline-block h-2 w-2 rounded-full transition-colors duration-300';
    
    switch(mood.state) {
        case 'Resting':
            indicatorEl.classList.add('bg-sky-400/70');
            break;
        case 'Intervened':
            indicatorEl.classList.add('bg-amber-400/80');
            break;
        case 'Concerned':
            indicatorEl.classList.add('bg-rose-400/80');
            break;
        default:
            indicatorEl.classList.add('bg-sky-400/70');
            break;
    }
}

// Automatically re-run when the timeline updates
const tlContainer = document.getElementById('timelineContainer');
if (tlContainer) {
    const observer = new MutationObserver(() => {
        initFrustrationTelemetryFromEpisodeLog();
    });
    observer.observe(tlContainer, { childList: true, subtree: true });
}

window.addEventListener('DOMContentLoaded', initFrustrationTelemetryFromEpisodeLog);
