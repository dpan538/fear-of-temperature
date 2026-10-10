"""Descriptive source-frame genres, never corpus labels or collector controls."""
METHOD = 'source-frame-genre-v2; source descriptions only; per-body genre unvalidated'

def genre(source_id, registry):
    explicit = {
        'python_list_archive':'technical_mailing_archive',
        'w3_wwwtalk':'technical_mailing_archive',
        'python_discourse':'technical_discussion_forum',
        'osm_discourse':'mapping_technical_discussion_forum',
        'hackernews':'technology_link_and_comment_network',
        'tildes':'multi_interest_public_topic_reply_community',
        'ilxor':'general_interest_discussion_board',
        'thesession':'traditional_music_discussion_community',
    }
    if source_id in explicit:return explicit[source_id]
    if source_id.startswith(('dowire_','mpls_')):return 'civic_mailing_archive'
    source=registry.get(source_id,{})
    return source.get('source_frame_purpose') or source.get('frame') or 'unresolved_source_frame'
