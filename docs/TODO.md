# TODO List for YouTube Study Buddy

## High Priority

### Error Handling
- [ ] Add fallback from ML models to keyword matching when models fail to load
- [ ] Improve error messages when Claude API fails
- [ ] Handle rate limiting with exponential backoff

### Testing
- [ ] Add unit tests for auto-categorization module
- [ ] Add unit tests for assessment generation
- [ ] Integration tests for full pipeline with ML features
- [ ] Test graceful degradation when models unavailable

## Medium Priority

### Features
- [ ] Add support for podcast transcripts (Spotify, Apple Podcasts)
- [ ] Implement answer evaluation system using semantic similarity
- [ ] Add progress tracking for learning goals
- [ ] Support for multiple Claude models (Opus, Sonnet, Haiku)

### Performance
- [ ] Implement caching for sentence transformer embeddings
- [ ] Optimize batch processing for large video lists
- [ ] Add GPU support for ML model inference

### UI/UX
- [ ] Improve Streamlit interface with assessment viewing
- [ ] Add configuration UI for ML model selection
- [ ] Progress bars for batch processing

## Low Priority

### Enhancements
- [ ] Fine-tune ML models on educational content
- [ ] Vector database integration for large knowledge bases
- [ ] Export to Anki flashcard format
- [ ] Multi-language support for non-English videos

### Documentation
- [ ] Add more Jupyter notebook tutorials
- [ ] Create video tutorial for setup and usage
- [ ] Document API for programmatic usage
- [ ] Add contributing guidelines

## Completed ✅
- [x] Implement auto-categorization with ML models
- [x] Generate learning assessments with One-Up Challenges
- [x] Add environment variable configuration for models
- [x] Update README with learning theory
- [x] Create learning notebooks for ML components

## Notes
- Focus on maintaining graceful degradation - all features should work without ML models
- Keep the tool free and accessible - no paid dependencies
- Prioritize educational value over feature complexity