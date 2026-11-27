"""
RIZYEE Creator Engine
=====================
Automatically generates professional presentation slide decks locally
based on your topic, with zero dependencies and zero cost.
"""

import os
import webbrowser
from rizyee.utils.logger import get_logger

logger = get_logger("actions.creator")


def create_project(project_name: str) -> str:
    if not project_name:
        project_name = "my_new_project"
    folder_name = project_name.strip().lower().replace(" ", "_")
    os.makedirs(folder_name, exist_ok=True)
    return folder_name


def create_document(filename: str, content: str = "") -> str:
    if not filename:
        filename = "document.txt"
    if not filename.endswith((".txt", ".md", ".py", ".html")):
        filename += ".txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content or f"Created by RIZYEE.\n")
    return filename


def create_presentation(topic: str) -> str:
    """
    Automatically generate a comprehensive 12-slide presentation based on the topic.
    """
    if not topic:
        topic = "Computer Networks"

    clean_topic = topic.strip().title()
    filename = f"presentation_{topic.strip().lower().replace(' ', '_')}.html"

    # Define smart slide generator based on topic
    slides_data = [
        {
            "title": clean_topic,
            "subtitle": "Comprehensive Presentation",
            "bullets": [
                "Generated automatically by RIZYEE AI Assistant",
                "Complete overview, architecture, and practical applications",
                "Use Left/Right arrow keys or buttons to navigate slides"
            ]
        },
        {
            "title": "Introduction & Overview",
            "subtitle": "What is " + clean_topic + "?",
            "bullets": [
                f"Fundamental definitions and core concepts of {clean_topic}.",
                "Historical background and evolution over time.",
                "Why this subject is vital in modern technology and computer science."
            ]
        },
        {
            "title": "Core Architecture",
            "subtitle": "Structure and Components",
            "bullets": [
                "Primary structural building blocks and components.",
                "How individual elements interact and communicate.",
                "System design principles and best practices."
            ]
        },
        {
            "title": "Key Protocols & Standards",
            "subtitle": "Rules of Operation",
            "bullets": [
                "Industry standards and governing specifications.",
                "Data transmission rules and synchronization.",
                "Ensuring reliability, consistency, and compliance."
            ]
        },
        {
            "title": "Working Mechanism",
            "subtitle": "Step-by-Step Execution",
            "bullets": [
                "Phase 1: Initialization and setup.",
                "Phase 2: Data processing and routing.",
                "Phase 3: Delivery, response, and verification."
            ]
        },
        {
            "title": "Security & Protection",
            "subtitle": "Safeguarding the System",
            "bullets": [
                "Identifying potential vulnerabilities and threat vectors.",
                "Encryption, authentication, and access control mechanisms.",
                "Mitigation strategies and disaster recovery planning."
            ]
        },
        {
            "title": "Performance Optimization",
            "subtitle": "Speed and Efficiency",
            "bullets": [
                "Bottleneck identification and latency reduction.",
                "Resource allocation, caching, and load balancing.",
                "Metrics and benchmarking for optimal output."
            ]
        },
        {
            "title": "Real-World Applications",
            "subtitle": "Practical Implementations",
            "bullets": [
                f"How industries and organizations utilize {clean_topic}.",
                "Case studies of successful deployments.",
                "Impact on daily productivity and technological advancement."
            ]
        },
        {
            "title": "Advantages & Benefits",
            "subtitle": "Why It Matters",
            "bullets": [
                "Increased efficiency, automation, and scalability.",
                "Cost reduction and streamlined operations.",
                "Enhanced reliability and user experience."
            ]
        },
        {
            "title": "Challenges & Limitations",
            "subtitle": "Overcoming Obstacles",
            "bullets": [
                "Technical hurdles and scaling constraints.",
                "Maintenance overhead and complexity management.",
                "Future research areas to solve current limitations."
            ]
        },
        {
            "title": "Future Trends",
            "subtitle": "What's Next?",
            "bullets": [
                "Emerging technologies and next-gen innovations.",
                "Integration with AI, automation, and cloud ecosystems.",
                "Predictions for the next decade."
            ]
        },
        {
            "title": "Conclusion & Q&A",
            "subtitle": "Summary",
            "bullets": [
                f"Recap of core takeaways regarding {clean_topic}.",
                "Continuous learning and adaptation in a fast-changing field.",
                "Thank you! Questions and Discussion."
            ]
        }
    ]

    # Build HTML slides dynamically
    slides_html = ""
    for i, s in enumerate(slides_data):
        active_class = "active" if i == 0 else ""
        bullets_li = "".join([f"<li>{b}</li>" for b in s["bullets"]])
        slides_html += f"""
        <div class="slide {active_class}">
            <h1>{s["title"]}</h1>
            <p class="subtitle">{s.get("subtitle", "")}</p>
            <ul>{bullets_li}</ul>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{clean_topic} — Presentation</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f172a 1e-15, #1e293b 100%, #111827 100%);
            background-color: #0f172a;
            color: #f8fafc;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }}
        .slides-container {{
            width: 85%;
            max-width: 1000px;
            height: 65vh;
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 50px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        .slide {{
            display: none;
        }}
        .slide.active {{
            display: block;
            animation: fadeIn 0.4s ease-in-out;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        h1 {{ font-size: 2.6em; margin-bottom: 5px; color: #38bdf8; }}
        .subtitle {{ font-size: 1.4em; color: #cbd5e1; margin-bottom: 25px; font-weight: 600; }}
        ul {{ font-size: 1.25em; line-height: 1.7; color: #e2e8f0; }}
        li {{ margin-bottom: 14px; }}
        .nav-buttons {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 30px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            padding-top: 20px;
        }}
        button {{
            background: #3b82f6;
            color: white;
            border: none;
            padding: 12px 24px;
            font-size: 1em;
            font-weight: bold;
            border-radius: 10px;
            cursor: pointer;
            transition: background 0.2s, transform 0.1s;
        }}
        button:hover {{ background: #2563eb; transform: translateY(-2px); }}
        button:active {{ transform: translateY(0); }}
        .slide-number {{
            font-size: 1em;
            color: #94a3b8;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="slides-container">
        {slides_html}

        <div class="nav-buttons">
            <button onclick="prevSlide()">← Previous</button>
            <div class="slide-number" id="slideNum">Slide 1 of {len(slides_data)}</div>
            <button onclick="nextSlide()">Next →</button>
        </div>
    </div>

    <script>
        let currentSlide = 0;
        const slides = document.querySelectorAll('.slide');
        const slideNum = document.getElementById('slideNum');

        function showSlide(index) {{
            slides.forEach((slide, i) => {{
                slide.classList.remove('active');
                if (i === index) {{
                    slide.classList.add('active');
                }}
            }});
            slideNum.innerText = `Slide ${{index + 1}} of ${{slides.length}}`;
        }}

        function nextSlide() {{
            currentSlide = (currentSlide + 1) % slides.length;
            showSlide(currentSlide);
        }}

        function prevSlide() {{
            currentSlide = (currentSlide - 1 + slides.length) % slides.length;
            showSlide(currentSlide);
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowRight' || e.key === ' ') nextSlide();
            if (e.key === 'ArrowLeft') prevSlide();
        }});
    </script>
</body>
</html>
"""

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    abs_path = os.path.abspath(filename)
    webbrowser.open(f"file:///{abs_path.replace(os.sep, '/')}")
    logger.info(f"Generated 12-slide presentation for {clean_topic}: {filename}")
    return clean_topic
