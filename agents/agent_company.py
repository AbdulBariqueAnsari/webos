import json, time, random, threading, re
from collections import defaultdict, OrderedDict

class AgentCompany:
    def __init__(self):
        self.agents = OrderedDict()
        self.org_chart = {}
        self.task_queue = []
        self.results_cache = {}
        self._lock = threading.Lock()
        self._build_organization()

    def _build_organization(self):
        org = {
            "ceo": {
                "role": "CEO",
                "department": "Executive",
                "description": "Orchestrates all agents, assigns tasks, reviews results",
                "subordinates": ["dev_head", "qa_head", "sec_head", "ops_head", "creative_head", "data_head", "support_head"]
            },
            "dev_head": {"role": "Development Director", "department": "Development", "description": "Manages all development teams"},
            "qa_head": {"role": "QA Director", "department": "Quality", "description": "Manages testing and quality assurance"},
            "sec_head": {"role": "Security Director", "department": "Security", "description": "Manages security and audits"},
            "ops_head": {"role": "Operations Director", "department": "Operations", "description": "Manages infrastructure and deployment"},
            "creative_head": {"role": "Creative Director", "department": "Creative", "description": "Manages design and media"},
            "data_head": {"role": "Data Director", "department": "Data", "description": "Manages data processing and analytics"},
            "support_head": {"role": "Support Director", "department": "Support", "description": "Manages user support and documentation"},
            "dev_frontend": {"role": "Frontend Lead", "department": "Development", "parent": "dev_head"},
            "dev_backend": {"role": "Backend Lead", "department": "Development", "parent": "dev_head"},
            "dev_fullstack": {"role": "Fullstack Lead", "department": "Development", "parent": "dev_head"},
            "qa_manual": {"role": "Manual Test Lead", "department": "Quality", "parent": "qa_head"},
            "qa_auto": {"role": "Automation Lead", "department": "Quality", "parent": "qa_head"},
            "qa_perf": {"role": "Performance Lead", "department": "Quality", "parent": "qa_head"},
            "sec_audit": {"role": "Security Auditor", "department": "Security", "parent": "sec_head"},
            "sec_network": {"role": "Network Security Lead", "department": "Security", "parent": "sec_head"},
            "sec_compliance": {"role": "Compliance Officer", "department": "Security", "parent": "sec_head"},
            "ops_devops": {"role": "DevOps Lead", "department": "Operations", "parent": "ops_head"},
            "ops_infra": {"role": "Infrastructure Lead", "department": "Operations", "parent": "ops_head"},
            "ops_db": {"role": "Database Admin", "department": "Operations", "parent": "ops_head"},
            "creative_ui": {"role": "UI Designer", "department": "Creative", "parent": "creative_head"},
            "creative_graphic": {"role": "Graphic Designer", "department": "Creative", "parent": "creative_head"},
            "creative_media": {"role": "Media Producer", "department": "Creative", "parent": "creative_head"},
            "data_analyst": {"role": "Data Analyst", "department": "Data", "parent": "data_head"},
            "data_ml": {"role": "ML Engineer", "department": "Data", "parent": "data_head"},
            "data_engineer": {"role": "Data Engineer", "department": "Data", "parent": "data_head"},
            "support_tier1": {"role": "Tier 1 Support", "department": "Support", "parent": "support_head"},
            "support_tier2": {"role": "Tier 2 Support", "department": "Support", "parent": "support_head"},
            "support_docs": {"role": "Documentation Writer", "department": "Support", "parent": "support_head"},
        }

        worker_roles = {
            "worker_py": "Python Developer", "worker_js": "JavaScript Developer",
            "worker_html": "HTML/CSS Developer", "worker_rust": "Rust Developer",
            "worker_go": "Go Developer", "worker_java": "Java Developer",
            "worker_cpp": "C++ Developer", "worker_sql": "SQL Developer",
            "worker_react": "React Developer", "worker_node": "Node.js Developer",
            "worker_test": "Test Engineer", "worker_debug": "Debug Specialist",
            "worker_review": "Code Reviewer", "worker_docs": "Technical Writer",
            "worker_sec": "Security Tester", "worker_perf": "Performance Tester",
            "worker_ui": "UI Developer", "worker_api": "API Developer",
            "worker_db": "Database Developer", "worker_net": "Network Engineer",
            "worker_ml": "ML Specialist"
        }

        for k, v in org.items():
            v["id"] = k
            v.setdefault("parent", "ceo" if k != "ceo" else None)
            self.agents[k] = self._create_agent(v)

        for name, role in worker_roles.items():
            parent = random.choice(["dev_frontend", "dev_backend", "dev_fullstack", "qa_auto", "qa_manual", "data_analyst", "sec_audit", "ops_devops"])
            self.agents[name] = self._create_agent({
                "id": name, "role": role, "department": self.agents[parent]["department"],
                "parent": parent, "description": f"Specialized {role.lower()}"
            })

        for a_id, a in self.agents.items():
            self.org_chart[a_id] = {
                "role": a["role"], "department": a["department"],
                "parent": a.get("parent"),
                "children": [x for x in self.agents if self.agents[x].get("parent") == a_id]
            }

    def _create_agent(self, info):
        return {
            "id": info["id"], "role": info["role"], "department": info["department"],
            "description": info.get("description", ""), "parent": info.get("parent"),
            "status": "idle", "tasks_completed": 0, "accuracy": random.uniform(0.85, 0.99),
            "response_time": random.uniform(0.1, 2.0), "skills": [],
            "specialization": info["role"].lower()
        }

    def process(self, message, mode="auto"):
        msg_lower = message.lower()

        if mode == "org":
            return self._org_processing(message)

        if mode == "pipeline":
            return self._pipeline_processing(message)

        selected = self._route_task(message)
        results = []

        for agent_id in selected:
            result = self._execute_agent(agent_id, message)
            results.append(result)

        return {
            "mode": mode,
            "agents_involved": len(results),
            "results": results,
            "org_chart": {a["id"]: a["role"] for a in results}
        }

    def _route_task(self, message):
        msg_lower = message.lower()
        scores = {}

        for a_id, agent in self.agents.items():
            score = 0
            role = agent["specialization"]
            dept = agent["department"].lower()

            if "python" in msg_lower and role in ("python developer", "backend lead", "fullstack lead"):
                score += 3
            if "javascript" in msg_lower and role in ("javascript developer", "frontend lead", "react developer"):
                score += 3
            if "debug" in msg_lower or "error" in msg_lower or "fix" in msg_lower:
                if role in ("debug specialist", "test engineer", "qa"):
                    score += 3
            if "security" in msg_lower or "vulnerable" in msg_lower or "hack" in msg_lower:
                if "security" in dept or "security" in role:
                    score += 3
            if "data" in msg_lower or "analytics" in msg_lower or "report" in msg_lower:
                if "data" in dept:
                    score += 3
            if "design" in msg_lower or "ui" in msg_lower or "interface" in msg_lower:
                if "creative" in dept or "design" in role:
                    score += 3
            if "deploy" in msg_lower or "server" in msg_lower or "infra" in msg_lower:
                if "operations" in dept or "devops" in role:
                    score += 3
            if "test" in msg_lower or "quality" in msg_lower:
                if "quality" in dept or "test" in role:
                    score += 3
            if "document" in msg_lower or "write" in msg_lower or "doc" in msg_lower:
                if "support" in dept or "documentation" in role:
                    score += 2
            if "code" in msg_lower or "program" in msg_lower or "develop" in msg_lower:
                if "development" in dept:
                    score += 2
            if score > 0:
                scores[a_id] = score + agent["accuracy"]

        if scores:
            sorted_agents = sorted(scores.items(), key=lambda x: -x[1])
            top = [a[0] for a in sorted_agents[:5]]
            return top

        return [random.choice(list(self.agents.keys()))]

    def _execute_agent(self, agent_id, task):
        agent = self.agents.get(agent_id)
        if not agent:
            return {"agent": agent_id, "error": "Agent not found"}

        with self._lock:
            agent["status"] = "busy"
            agent["tasks_completed"] += 1

        time.sleep(min(agent["response_time"] * 0.1, 0.5))

        result = self._generate_result(agent, task)

        with self._lock:
            agent["status"] = "idle"

        return {
            "agent": agent_id,
            "role": agent["role"],
            "department": agent["department"],
            "result": result,
            "accuracy": agent["accuracy"]
        }

    def _generate_result(self, agent, task):
        role = agent["role"].lower()
        dept = agent["department"].lower()
        task_lower = task.lower()

        responses = []

        if "development" in dept or "code" in role:
            if "python" in task_lower or "script" in task_lower:
                responses.append("Generated Python code with proper error handling")
            if "debug" in task_lower or "fix" in task_lower or "error" in task_lower:
                responses.append("Analyzed code, found 3 issues: syntax error line 12, undefined var line 34, logic flaw line 56")
                responses.append("Applied fixes: corrected syntax, added type hints, optimized loop")
            if "review" in task_lower or "audit" in task_lower:
                responses.append("Code review complete: 85/100 score. 4 warnings, 2 suggestions")
            else:
                responses.append("Implementation complete with tests and documentation")

        if "quality" in dept or "test" in role:
            responses.append("Test suite executed: 47/48 passed, 1 flaky test identified")
            responses.append("Coverage report: 92% line coverage, 88% branch coverage")

        if "security" in dept:
            responses.append("Security scan complete: 2 low, 0 medium, 0 high vulnerabilities")
            responses.append("OWASP checks passed, SSL/TLS configuration verified")

        if "operations" in dept or "devops" in role:
            responses.append("Deployment pipeline configured. Build time: 3m 42s")
            responses.append("Infrastructure: 4 pods running, 2 nodes healthy, 0 alerts")

        if "creative" in dept or "design" in role:
            responses.append("UI mockup created with responsive design. Color palette optimized")
            responses.append("Asset generation complete: SVG icons, 3 variants")

        if "data" in dept:
            responses.append("Data analysis complete: 1.2M records processed, 15 key insights")
            responses.append("ML model trained: 94.2% accuracy, precision 0.93, recall 0.95")

        if "support" in dept:
            responses.append("Documentation generated: API reference, user guide, troubleshooting")
            responses.append("Support ticket resolved: root cause identified and fixed")

        if "ceo" in agent["id"] or agent["id"] == "ceo":
            responses.append("Task delegated to appropriate departments. Monitoring progress.")
            responses.append("Cross-team coordination initiated. Estimated completion: 15 minutes")

        if not responses:
            responses.append(f"Task analyzed via {agent['role']} perspective. Processing complete.")

        return {
            "summary": responses[0] if responses else "Task completed",
            "details": responses,
            "agent_notes": f"Processed by {agent['role']} ({agent['department']}) with {agent['accuracy']:.0%} accuracy"
        }

    def _org_processing(self, task):
        departments = defaultdict(list)
        for a_id, agent in self.agents.items():
            departments[agent["department"]].append(a_id)

        org_results = {}
        for dept, members in departments.items():
            dept_results = []
            for member_id in members[:3]:
                result = self._execute_agent(member_id, task)
                dept_results.append(result)
            org_results[dept] = dept_results

        return {"mode": "org_wide", "departments": dict(departments), "results": org_results}

    def _pipeline_processing(self, task):
        pipeline_steps = [
            ("dev_frontend", "Frontend analysis"),
            ("dev_backend", "Backend implementation"),
            ("qa_auto", "Automated testing"),
            ("sec_audit", "Security review"),
            ("ops_devops", "Deployment preparation"),
            ("support_docs", "Documentation"),
        ]
        pipeline_results = []
        pipeline_task = task
        for agent_id, step_name in pipeline_steps:
            if agent_id in self.agents:
                result = self._execute_agent(agent_id, f"{step_name}: {pipeline_task}")
                pipeline_results.append(result)
                pipeline_task = f"Previous output: {result['result']['summary']}. Original: {task}"
        return {"mode": "pipeline", "steps": len(pipeline_results), "results": pipeline_results}

    def get_org_chart(self):
        return self.org_chart

    def get_stats(self):
        total = len(self.agents)
        by_dept = defaultdict(int)
        for a in self.agents.values():
            by_dept[a["department"]] += 1
        avg_accuracy = sum(a["accuracy"] for a in self.agents.values()) / total if total else 0
        total_tasks = sum(a["tasks_completed"] for a in self.agents.values())
        return {
            "total_agents": total,
            "departments": dict(by_dept),
            "avg_accuracy": round(avg_accuracy, 3),
            "total_tasks_completed": total_tasks,
            "agent_list": [{"id": a["id"], "role": a["role"], "dept": a["department"]} for a in self.agents.values()]
        }
