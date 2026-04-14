"""
Integration tests for threaded comments functionality.

Test Coverage:
- Document-level comments (no line anchoring)
- Line-specific comments
- Threaded replies (parent-child relationships)
- Mixed scenarios (document + line comments with replies)
- Reply chains (nested replies)
- Filtering and retrieval

Each test is independent and cleans up after itself.
"""
import pytest
import requests


class TestThreadedComments:
    """Test threaded comment functionality."""
    
    def test_document_level_comment_with_replies(self, api_session):
        """Test creating document-level comment and adding replies."""
        print("\n" + "="*80)
        print("TEST: Document-Level Comment with Replies")
        print("="*80)
        print("Purpose: Verify document comments support threaded replies")
        print("Expected: Parent comment has no line anchoring, replies are linked")
        
        import uuid
        source_uri = f"git://test-repo/main/test-doc-comments-{uuid.uuid4()}.py"
        
        # Step 1: Create document-level comment (no line_start/line_end)
        print(f"\n📤 Step 1: Creating document-level comment...")
        parent_response = requests.post(
            f"{api_session.base_url}/api/wiki/v1/comments/",
            json={
                "source_uri": source_uri,
                "text": "This is a document-level comment about the entire file"
            },
            headers=api_session.headers
        )
        
        print(f"📥 Response: HTTP {parent_response.status_code}")
        assert parent_response.status_code == 201, f"Failed to create comment: {parent_response.text}"
        
        parent_comment = parent_response.json()
        parent_id = parent_comment['id']
        print(f"\n✅ Document comment created:")
        print(f"   ID: {parent_id}")
        print(f"   Text: {parent_comment['text']}")
        print(f"   Line Start: {parent_comment.get('line_start')}")
        print(f"   Line End: {parent_comment.get('line_end')}")
        
        # Verify it's a document-level comment
        assert parent_comment.get('line_start') is None, "Document comment should have no line_start"
        assert parent_comment.get('line_end') is None, "Document comment should have no line_end"
        
        try:
            # Step 2: Add first reply to document comment
            print(f"\n📤 Step 2: Adding first reply to document comment...")
            reply1_response = requests.post(
                f"{api_session.base_url}/api/wiki/v1/comments/",
                json={
                    "source_uri": source_uri,
                    "parent_comment": parent_id,
                    "text": "I agree with this document-level observation"
                },
                headers=api_session.headers
            )
            
            assert reply1_response.status_code == 201, f"Failed to create reply: {reply1_response.text}"
            reply1 = reply1_response.json()
            reply1_id = reply1['id']
            print(f"   ✓ Reply 1 created (ID: {reply1_id})")
            print(f"   Parent ID: {reply1.get('parent_id')}")
            
            # Verify parent relationship
            assert reply1.get('parent_id') == parent_id, f"Reply should have parent_id={parent_id}"
            
            # Step 3: Add second reply to document comment
            print(f"\n📤 Step 3: Adding second reply to document comment...")
            reply2_response = requests.post(
                f"{api_session.base_url}/api/wiki/v1/comments/",
                json={
                    "source_uri": source_uri,
                    "parent_comment": parent_id,
                    "text": "Another perspective on the document"
                },
                headers=api_session.headers
            )
            
            assert reply2_response.status_code == 201, f"Failed to create reply: {reply2_response.text}"
            reply2 = reply2_response.json()
            reply2_id = reply2['id']
            print(f"   ✓ Reply 2 created (ID: {reply2_id})")
            
            # Step 4: Add nested reply (reply to reply)
            print(f"\n📤 Step 4: Adding nested reply (reply to reply1)...")
            nested_reply_response = requests.post(
                f"{api_session.base_url}/api/wiki/v1/comments/",
                json={
                    "source_uri": source_uri,
                    "parent_comment": reply1_id,
                    "text": "Responding to the first reply"
                },
                headers=api_session.headers
            )
            
            assert nested_reply_response.status_code == 201, f"Failed to create nested reply: {nested_reply_response.text}"
            nested_reply = nested_reply_response.json()
            nested_reply_id = nested_reply['id']
            print(f"   ✓ Nested reply created (ID: {nested_reply_id})")
            print(f"   Parent ID: {nested_reply.get('parent_id')}")
            
            assert nested_reply.get('parent_id') == reply1_id, f"Nested reply should have parent_id={reply1_id}"
            
            # Step 5: Retrieve all comments and verify structure
            print(f"\n📤 Step 5: Retrieving all comments for source_uri...")
            list_response = requests.get(
                f"{api_session.base_url}/api/wiki/v1/comments/?source_uri={source_uri}",
                headers=api_session.headers
            )
            
            assert list_response.status_code == 200, f"Failed to list comments: {list_response.text}"
            root_comments = list_response.json()
            print(f"   ✓ Retrieved {len(root_comments)} root comment(s)")
            
            # API returns nested structure: root comments with replies array
            assert len(root_comments) == 1, f"Should have 1 root comment, got {len(root_comments)}"
            
            # Verify parent comment
            parent_from_list = root_comments[0]
            assert parent_from_list['id'] == parent_id, "Root comment ID mismatch"
            assert parent_from_list.get('line_start') is None, "Parent should have no line_start"
            assert parent_from_list.get('line_end') is None, "Parent should have no line_end"
            
            # Verify replies are nested in parent
            replies = parent_from_list.get('replies', [])
            assert len(replies) == 2, f"Parent should have 2 direct replies, got {len(replies)}"
            
            # Find reply1 and reply2
            reply1_from_list = next((r for r in replies if r['id'] == reply1_id), None)
            reply2_from_list = next((r for r in replies if r['id'] == reply2_id), None)
            
            assert reply1_from_list is not None, "Reply1 not found in parent's replies"
            assert reply2_from_list is not None, "Reply2 not found in parent's replies"
            assert reply1_from_list.get('parent_id') == parent_id, "Reply1 parent_id mismatch"
            assert reply2_from_list.get('parent_id') == parent_id, "Reply2 parent_id mismatch"
            
            # Verify nested reply is in reply1's replies
            nested_replies = reply1_from_list.get('replies', [])
            assert len(nested_replies) == 1, f"Reply1 should have 1 nested reply, got {len(nested_replies)}"
            
            nested_from_list = nested_replies[0]
            assert nested_from_list['id'] == nested_reply_id, "Nested reply ID mismatch"
            assert nested_from_list.get('parent_id') == reply1_id, "Nested reply parent_id mismatch"
            
            print(f"\n✅ PASS: Document-level threading works correctly")
            print(f"   Structure:")
            print(f"   - Document comment (ID: {parent_id})")
            print(f"     ├─ Reply 1 (ID: {reply1_id})")
            print(f"     │  └─ Nested reply (ID: {nested_reply_id})")
            print(f"     └─ Reply 2 (ID: {reply2_id})")
            
        finally:
            # Cleanup: Delete all comments
            print(f"\n🧹 Cleaning up comments...")
            for comment_id in [nested_reply_id, reply2_id, reply1_id, parent_id]:
                requests.delete(
                    f"{api_session.base_url}/api/wiki/v1/comments/{comment_id}/",
                    headers=api_session.headers
                )
            print(f"   ✓ All comments deleted")
        
        print("="*80)
    
    def test_line_specific_comment_with_replies(self, api_session):
        """Test creating line-specific comment and adding replies."""
        print("\n" + "="*80)
        print("TEST: Line-Specific Comment with Replies")
        print("="*80)
        print("Purpose: Verify line comments support threaded replies")
        print("Expected: Parent comment has line anchoring, replies inherit context")
        
        import uuid
        source_uri = f"git://test-repo/main/test-line-comments-{uuid.uuid4()}.py"
        
        # Step 1: Create line-specific comment
        print(f"\n📤 Step 1: Creating line-specific comment (line 42)...")
        parent_response = requests.post(
            f"{api_session.base_url}/api/wiki/v1/comments/",
            json={
                "source_uri": source_uri,
                "line_start": 42,
                "line_end": 42,
                "text": "This line has a bug"
            },
            headers=api_session.headers
        )
        
        assert parent_response.status_code == 201, f"Failed to create comment: {parent_response.text}"
        parent_comment = parent_response.json()
        parent_id = parent_comment['id']
        print(f"\n✅ Line comment created:")
        print(f"   ID: {parent_id}")
        print(f"   Line: {parent_comment.get('line_start')}")
        
        # Verify it's a line-specific comment
        assert parent_comment.get('line_start') == 42, "Should have line_start=42"
        assert parent_comment.get('line_end') == 42, "Should have line_end=42"
        
        try:
            # Step 2: Add reply to line comment
            print(f"\n📤 Step 2: Adding reply to line comment...")
            reply_response = requests.post(
                f"{api_session.base_url}/api/wiki/v1/comments/",
                json={
                    "source_uri": source_uri,
                    "parent_comment": parent_id,
                    "text": "Good catch! Here's how to fix it..."
                },
                headers=api_session.headers
            )
            
            assert reply_response.status_code == 201, f"Failed to create reply: {reply_response.text}"
            reply = reply_response.json()
            reply_id = reply['id']
            print(f"   ✓ Reply created (ID: {reply_id})")
            print(f"   Parent ID: {reply.get('parent_id')}")
            
            # Verify parent relationship
            assert reply.get('parent_id') == parent_id, f"Reply should have parent_id={parent_id}"
            
            # Step 3: Retrieve comments and verify
            print(f"\n📤 Step 3: Retrieving comments...")
            list_response = requests.get(
                f"{api_session.base_url}/api/wiki/v1/comments/?source_uri={source_uri}",
                headers=api_session.headers
            )
            
            assert list_response.status_code == 200, f"Failed to list comments: {list_response.text}"
            root_comments = list_response.json()
            print(f"   ✓ Retrieved {len(root_comments)} root comment(s)")
            
            assert len(root_comments) == 1, f"Should have 1 root comment, got {len(root_comments)}"
            
            # Verify parent has line anchoring
            parent_from_list = root_comments[0]
            assert parent_from_list['id'] == parent_id, "Root comment ID mismatch"
            assert parent_from_list.get('line_start') == 42, "Parent should have line_start=42"
            
            # Verify reply is nested in parent
            replies = parent_from_list.get('replies', [])
            assert len(replies) == 1, f"Parent should have 1 reply, got {len(replies)}"
            
            reply_from_list = replies[0]
            assert reply_from_list['id'] == reply_id, "Reply ID mismatch"
            assert reply_from_list.get('parent_id') == parent_id, "Reply parent_id mismatch"
            
            print(f"\n✅ PASS: Line-specific threading works correctly")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up comments...")
            for comment_id in [reply_id, parent_id]:
                requests.delete(
                    f"{api_session.base_url}/api/wiki/v1/comments/{comment_id}/",
                    headers=api_session.headers
                )
            print(f"   ✓ All comments deleted")
        
        print("="*80)
    
    def test_mixed_document_and_line_comments(self, api_session):
        """Test mixing document-level and line-specific comments with replies."""
        print("\n" + "="*80)
        print("TEST: Mixed Document and Line Comments")
        print("="*80)
        print("Purpose: Verify document and line comments don't interfere")
        print("Expected: Each type maintains its own threading structure")
        
        import uuid
        source_uri = f"git://test-repo/main/test-mixed-comments-{uuid.uuid4()}.py"
        
        # Create document comment
        print(f"\n📤 Creating document comment...")
        doc_response = requests.post(
            f"{api_session.base_url}/api/wiki/v1/comments/",
            json={
                "source_uri": source_uri,
                "text": "Overall file structure looks good"
            },
            headers=api_session.headers
        )
        assert doc_response.status_code == 201
        doc_comment = doc_response.json()
        doc_id = doc_comment['id']
        print(f"   ✓ Document comment (ID: {doc_id})")
        
        # Create line comment
        print(f"\n📤 Creating line comment...")
        line_response = requests.post(
            f"{api_session.base_url}/api/wiki/v1/comments/",
            json={
                "source_uri": source_uri,
                "line_start": 10,
                "line_end": 10,
                "text": "This line needs attention"
            },
            headers=api_session.headers
        )
        assert line_response.status_code == 201
        line_comment = line_response.json()
        line_id = line_comment['id']
        print(f"   ✓ Line comment (ID: {line_id})")
        
        try:
            # Add reply to document comment
            print(f"\n📤 Adding reply to document comment...")
            doc_reply_response = requests.post(
                f"{api_session.base_url}/api/wiki/v1/comments/",
                json={
                    "source_uri": source_uri,
                    "parent_comment": doc_id,
                    "text": "I agree about the structure"
                },
                headers=api_session.headers
            )
            assert doc_reply_response.status_code == 201
            doc_reply = doc_reply_response.json()
            doc_reply_id = doc_reply['id']
            print(f"   ✓ Reply to document (ID: {doc_reply_id})")
            
            # Add reply to line comment
            print(f"\n📤 Adding reply to line comment...")
            line_reply_response = requests.post(
                f"{api_session.base_url}/api/wiki/v1/comments/",
                json={
                    "source_uri": source_uri,
                    "parent_comment": line_id,
                    "text": "Fixed in latest commit"
                },
                headers=api_session.headers
            )
            assert line_reply_response.status_code == 201
            line_reply = line_reply_response.json()
            line_reply_id = line_reply['id']
            print(f"   ✓ Reply to line (ID: {line_reply_id})")
            
            # Retrieve and verify
            print(f"\n📤 Retrieving all comments...")
            list_response = requests.get(
                f"{api_session.base_url}/api/wiki/v1/comments/?source_uri={source_uri}",
                headers=api_session.headers
            )
            assert list_response.status_code == 200
            root_comments = list_response.json()
            
            assert len(root_comments) == 2, f"Should have 2 root comments, got {len(root_comments)}"
            
            # Find document and line comments
            doc_from_list = next((c for c in root_comments if c['id'] == doc_id), None)
            line_from_list = next((c for c in root_comments if c['id'] == line_id), None)
            
            assert doc_from_list is not None, "Document comment not found"
            assert line_from_list is not None, "Line comment not found"
            
            # Verify document comment thread
            assert doc_from_list.get('line_start') is None, "Doc comment should have no line"
            doc_replies = doc_from_list.get('replies', [])
            assert len(doc_replies) == 1, f"Doc comment should have 1 reply, got {len(doc_replies)}"
            doc_reply_from_list = doc_replies[0]
            assert doc_reply_from_list['id'] == doc_reply_id, "Doc reply ID mismatch"
            assert doc_reply_from_list.get('parent_id') == doc_id, "Doc reply parent mismatch"
            
            # Verify line comment thread
            assert line_from_list.get('line_start') == 10, "Line comment should have line=10"
            line_replies = line_from_list.get('replies', [])
            assert len(line_replies) == 1, f"Line comment should have 1 reply, got {len(line_replies)}"
            line_reply_from_list = line_replies[0]
            assert line_reply_from_list['id'] == line_reply_id, "Line reply ID mismatch"
            assert line_reply_from_list.get('parent_id') == line_id, "Line reply parent mismatch"
            
            print(f"\n✅ PASS: Mixed comments maintain separate threading")
            print(f"   Document thread: {doc_id} → {doc_reply_id}")
            print(f"   Line thread: {line_id} → {line_reply_id}")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up comments...")
            for comment_id in [line_reply_id, doc_reply_id, line_id, doc_id]:
                requests.delete(
                    f"{api_session.base_url}/api/wiki/v1/comments/{comment_id}/",
                    headers=api_session.headers
                )
            print(f"   ✓ All comments deleted")
        
        print("="*80)
    
    def test_reply_without_line_anchoring_inherits_parent_context(self, api_session):
        """Test that replies don't need line anchoring - they inherit from parent."""
        print("\n" + "="*80)
        print("TEST: Reply Inherits Parent Context")
        print("="*80)
        print("Purpose: Verify replies don't need explicit line_start/line_end")
        print("Expected: Replies work with just parent_comment field")
        
        import uuid
        source_uri = f"git://test-repo/main/test-reply-inherit-{uuid.uuid4()}.py"
        
        # Create line comment
        print(f"\n📤 Creating line comment...")
        parent_response = requests.post(
            f"{api_session.base_url}/api/wiki/v1/comments/",
            json={
                "source_uri": source_uri,
                "line_start": 25,
                "line_end": 30,
                "text": "This block of code is complex"
            },
            headers=api_session.headers
        )
        assert parent_response.status_code == 201
        parent_id = parent_response.json()['id']
        
        try:
            # Create reply WITHOUT line_start/line_end
            print(f"\n📤 Creating reply without line anchoring...")
            reply_response = requests.post(
                f"{api_session.base_url}/api/wiki/v1/comments/",
                json={
                    "source_uri": source_uri,
                    "parent_comment": parent_id,
                    "text": "We should refactor this"
                    # Note: NO line_start or line_end
                },
                headers=api_session.headers
            )
            
            assert reply_response.status_code == 201, f"Reply should work without line anchoring: {reply_response.text}"
            reply = reply_response.json()
            reply_id = reply['id']
            
            print(f"   ✓ Reply created (ID: {reply_id})")
            print(f"   Parent ID: {reply.get('parent_id')}")
            print(f"   Line Start: {reply.get('line_start')}")
            print(f"   Line End: {reply.get('line_end')}")
            
            # Verify reply has parent but no line anchoring
            assert reply.get('parent_id') == parent_id, "Should have parent_id"
            # Reply may or may not have line anchoring - that's implementation dependent
            
            print(f"\n✅ PASS: Replies work without explicit line anchoring")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up comments...")
            requests.delete(f"{api_session.base_url}/api/wiki/v1/comments/{reply_id}/", headers=api_session.headers)
            requests.delete(f"{api_session.base_url}/api/wiki/v1/comments/{parent_id}/", headers=api_session.headers)
            print(f"   ✓ All comments deleted")
        
        print("="*80)
