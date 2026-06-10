# CV -- Mahadev Mahesh Maitri

**Location:** New York City, NY
**Email:** mahadev@maitri.pro
**LinkedIn:** linkedin.com/in/mahadev-maitri
**Portfolio:** maitri.pro
**GitHub:** github.com/mahadev9

## Professional Summary

AI Engineer with 4+ years building and deploying production AI systems, specializing in Generative AI, Large Language Models (LLMs),
Retrieval-Augmented Generation (RAG), and AI agents on AWS. Shipped an enterprise document-intelligence platform on AWS Bedrock
(Claude) with a serverless, event-driven architecture achieving 92% extraction confidence and 99.8% availability at 300+ concurrent requests. Skilled in Python, LangChain/LangGraph, vector databases, LLM fine-tuning (QLoRA), and MLOps.

## Work Experience

### Fulcrum Digital  --  New York City, NY
**AI Engineer**
Oct 2024 - Present


- Architected an enterprise document intelligence solution achieving 92% average extraction confidence and 40% reduction in manual data entry, by designing Doxtract-IDP using AWS Bedrock multi-modal models (Claude Sonnet 4) with a serverless Lambda-SQS-DynamoDB event-driven architecture.
- Implemented production-grade document processing with 90%+ field-level extraction accuracy via human-in-the-loop validation and post-processing rules, deployed on serverless AWS infrastructure handling 60600 second processing windows per document.
- Designed and deployed high-throughput microservices on AWS EKS with horizontal pod autoscaling, load balancing, and CI/CD pipelines, delivering 99.8% system availability while handling 300+ concurrent requests during peak usage.
- Architected an event-driven GenAI pipeline using LangGraph agent systems with persistent memory and chain-of-thought reasoning, improving response relevance scores by 20% and reducing manual policy review time by 15%.
- Engineered a custom vector database retriever with LLM-based reranking, increasing search relevance scores by 25% and achieving 87% precision across 2,000+ synthetic insurance risk scenarios.
- Optimized GPU infrastructure costs by migrating from local Ollama deployments to AWS Bedrock API integration, eliminating on-premise GPU dependencies and reducing monthly EC2 spend by 60%.
- Deployed a self-hosted OCR service using Vision Transformer (Phi3.5 Vision) on EKS with Ray clusters for distributed computing, reducing monthly infrastructure costs by 20%.
- Built a RAG pipeline with Kafka-based document ingestion and Redis query caching, implementing custom retrieval and reranking components with structured claim analysis to achieve 87% precision on insurance risk assessment across 2,000+ test scenarios.

### Department of Mechanical Engineering - University of Delaware  --  Newark, DE
**Research Assistant**
Jan 2024 - Feb 2025

- Engineered a real-time intersection detection algorithm with sub-100ms latency by integrating live MQTT signal data with the Google Maps API, enabling high-speed spatial indexing and predictive navigation.
- Developed a cross-platform mobile application that surfaces autonomous traffic alerts, utilizing real-time sensor fusion to improve driver decision-making and safety at high-traffic intersections.
- Deployed a predictive ”dilemma zone” alert system that notifies users 8 seconds prior to intersection entry using real-time traffic data, successfully reducing red-light violations and improving road safety in simulated tests.

### Optum - UnitedHealth Group  --  Bengaluru, India
**Software Engineer**
Jul 2020 - Jul 2022

- Designed ETL pipelines using Python and AWS Glue to migrate 100,000+ records with 98% accuracy from legacy systems to AWS Redshift, ensuring seamless data transfer and centralized warehousing.
- Engineered NLP pipelines using SpaCy and NLTK to parse eligibility criteria and applicant details from 10,000+ forms automatically, improving data extraction accuracy by 95% with predictive models deployed on AWS SageMaker.
- Integrated OCR using Tesseract to automate data entry from 5,000+ scanned forms, increasing document processing efficiency by 85% and accelerating downstream workflows.
- Built low-latency REST APIs using FastAPI, integrating NLP and OCR models with PyTorch deep learning for real-time eligibility assessments, achieving 95% accuracy in incoming application processing.
- Executed functional regression testing with Robot Framework and performance testing with JMeter, ensuring 97% SLA compliance for RESTful APIs in the OMMS project through bi-weekly test suite execution and analysis.

## Projects

### Identifying Student Misconceptions in Math with Fine-Tuned LLMs
Jul 2025 - Oct 2025

- Developed a multi-model classification system by fine-tuning a diverse range of LLMs, including DeepSeek, Gemma-2, and Qwen3.
- Employed advanced parameter-efficient fine-tuning (PEFT) techniques like QLoRA with 4-bit quantization and Out-of-Fold (OOF) training to maximize model performance and robustness on imbalanced data.
- Optimized final prediction accuracy by engineering an ensembling pipeline that aggregated model outputs through weighted averaging and a custom disagreement-handling algorithm, effectively leveraging the strengths of diverse architectures.
- Achieved a final Mean Average Precision (MAP@3) score of 0.948, demonstrating the system’s high accuracy in classifying nuanced mathematical misconceptions from student explanations.

### Formula 1 Race Strategy Optimization with Deep Reinforcement Learning
Feb 2024 - May 2024

- Designed and trained a Deep Q-Learning agent to optimize race strategies in Formula 1 by creating a data-driven environment using real-world racing data from FastF1.
- Developed a Markov Decision Process (MDP) with a reward system that considers pit stop penalties, tire wear, and lap times, enabling the agent to make strategic decisions about pit stops and tire selection to achieve optimal race performance.

## Education

- Master of Science in Computer Science, University of Delaware (2024)
- Bachelor of Engineering in Electronics and Communication Engineering, R V College of Engineering (2020)

## Skills

- **Programming Languages**: Python, JavaScript, TypeScript, C/C++, Kotlin, HTML, CSS, SQL, Golang, GraphQL
- **Frameworks**: Node.js, React, Bootstrap, Redux, Next.js, TailwindCSS, Flutter, FastAPI
- **Testing Frameworks**: JUnit, Jest, Robot Framework, Selenium
- **Cloud & Databases**: Amazon Web Services (EC2, ECR, EKS, Bedrock, MemoryDB, EBS, EFS, S3, SQS, Lambda, DynamoDB, RDS ), Google Cloud, MongoDB, PostgreSQL, Google Firebase, Docker, Kubernetes
- **ML Libraries**: PyTorch, TensorFlow, HuggingFace (Transformers, peft), LangChain, LangGraph, MCP (Model Context Protocol), Keras, Scikit-Learn, Gymnasium
