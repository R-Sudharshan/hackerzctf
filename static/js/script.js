document.addEventListener('DOMContentLoaded', () => {
    // Console easter egg
    console.log("%c HACKERZ CTF \n SYSTEM ACCESS GRANTED ", "color: #00ff41; background: #000; font-size: 20px; padding: 10px; border: 2px solid #00ff41;");

    // Modal Handling
    const modalButtons = document.querySelectorAll('.btn-solve');
    const modalOverlay = document.getElementById('modal');

    // Create Modal HTML if not exists
    if (!modalOverlay.innerHTML) {
        modalOverlay.innerHTML = `
            <div class="modal-content">
                <span class="close-modal">&times;</span>
                <h2 id="modal-title">Challenge</h2>
                <p id="modal-desc">Enter the flag to solve this challenge.</p>
                <div class="input-group">
                    <input type="text" id="flag-input" class="flag-input" placeholder="flag{...}">
                </div>
                <button id="submit-btn" class="cta-button" style="width: 100%; margin-top: 1rem;">Submit</button>
            </div>
        `;
        modalOverlay.classList.add('modal-overlay');
    }

    const modalTitle = document.getElementById('modal-title');
    const closeBtn = document.querySelector('.close-modal');
    const submitBtn = document.getElementById('submit-btn');
    let currentChallengeId = null;

    modalButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            // If it's a download link, let it download, but ALSO open modal if they want to submit
            // Actually, usually you download first then come back. But let's allow both.
            if (!btn.hasAttribute('download')) {
                e.preventDefault();
            }

            const challengeName = btn.parentElement.querySelector('h4').innerText;
            currentChallengeId = btn.getAttribute('data-id');

            modalTitle.innerText = challengeName;
            modalOverlay.classList.add('modal-active');
        });
    });

    submitBtn.addEventListener('click', async () => {
        const flag = document.getElementById('flag-input').value;

        if (!flag) {
            alert("Please enter the Flag!");
            return;
        }

        try {
            const response = await fetch('/api/solve', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    challenge_id: currentChallengeId,
                    flag: flag
                })
            });

            const result = await response.json();

            if (result.success) {
                alert(`SUCCESS: ${result.message}\nNew Score: ${result.score}`);
                location.reload(); // Reload to update leaderboard
            } else {
                alert(`FAILED: ${result.message}`);
            }
        } catch (err) {
            console.error(err);
            alert("Error submitting flag.");
        }
    });

    closeBtn.addEventListener('click', () => {
        modalOverlay.classList.remove('modal-active');
    });

    // Close on outside click
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) {
            modalOverlay.classList.remove('modal-active');
        }
    });

    // Glitch effect enhancement (random text scramble)
    const titles = document.querySelectorAll('.glitch');
    titles.forEach(title => {
        title.setAttribute('data-text', title.innerText);
    });
});
