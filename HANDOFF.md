# LLM-e
**Cross-Platform Hardware Scanner and AI Model Recommender Module**

## Project Overview
LLM-e is a standalone, distributable Python module designed to be hardware and software agnostic (macOS, Windows, Linux). It profiles the local device's hardware, queries cloud AI model APIs (like NVIDIA NIM), and filters local models that fit and run with conversational speed on the scanned hardware.

It outputs professional-grade HTML instructions to help human users install the recommended models, and generates system-readable JSON configs for orchestration layers.

## Core Features
- Hardware scanning (`psutil`, platform APIs) for CPU, RAM, and Disk space.
- Cloud Model Discovery (Top 5 fast, smart, easy-to-use).
- Local Model Capability matching (Strict constraints for conversational speed based on hardware).
- Clean, overwrite-only HTML documentation generator.

## Status
- Initializing (Phase 1)
