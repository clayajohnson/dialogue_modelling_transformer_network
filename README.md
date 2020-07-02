# DMTNet
DMTNet stands for Dialogue Modelling Transformer Network - a novel implementation of state-of-the-art natural language processing (NLP) deep neural networks (DNNs)

## Goal
The aim of this project is to build an interactive deep-fake of celebrity intellectual Joe Rogan. Ideally, the application will simulate conversation by generating text responses in the style of Joe Rogan

## Implementation
The current implementation is a [Flask](http://flask.pocoo.org/) application that runs on a builtin server. Responses are generated with a custom version of OpenAI's GPT-2 which has been finetuned on transcripts of Joe Rogan's podcasts.
