SELECT * FROM job_postings_fact LIMIT 10;

SELECT *
FROM company_dim

SELECT *
FROM skills_job_dim

SELECT *
FROM skills_dim

SELECT
	job_title_short,
	COUNT(*) AS demand_jobs
FROM job_postings_fact
GROUP BY job_title_short
ORDER BY demand_jobs DESC;


-- Demanded skills DESC order
SELECT
	sd.skills,
	COUNT(*) AS demand_skills
FROM skills_job_dim sjd
JOIN skills_dim sd ON  sjd.skill_id = sd.skill_id
GROUP BY sd.skills
ORDER BY demand_skills DESC

-- join company table, job posting and skill job dim
SELECT
	sd.skills,
	COUNT(*) AS top_skills
FROM job_postings_fact jpf
JOIN skills_job_dim sjd ON jpf.job_id = sjd.job_id
JOIN skills_dim sd ON sjd.skill_id = sd.skill_id
-- WHERE jpf.job_title_short = 'Data Anayst'
GROUP BY sd.skills
ORDER BY top_skills DESC


-- top skills for a DA
SELECT
	sd.skills,
	COUNT(*) AS top_skills
FROM job_postings_fact jpf
JOIN skills_job_dim sjd ON jpf.job_id = sjd.job_id
JOIN skills_dim sd ON sjd.skill_id = sd.skill_id
WHERE jpf.job_title_short = 'Data Analyst'
GROUP BY sd.skills
ORDER BY top_skills DESC;

-- top skills for a DE
SELECT
	sd.skills,
	COUNT(*) AS top_skills
FROM job_postings_fact jpf
JOIN skills_job_dim sjd ON jpf.job_id = sjd.job_id
JOIN skills_dim sd ON sjd.skill_id = sd.skill_id
WHERE jpf.job_title_short = 'Data Engineer'
GROUP BY sd.skills
ORDER BY top-skills DESC;

	

