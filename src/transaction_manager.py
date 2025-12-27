"""
Transaction Manager for Web Extraction MCP
Handles transaction lifecycle, storage, and retrieval
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path


class TransactionManager:
    """Manage transaction lifecycle and storage for web extractions"""

    def __init__(self, data_dir: str = "./data"):
        """
        Initialize transaction manager.

        Args:
            data_dir: Root directory for storing transaction data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.data_dir / "transactions.index"
        self._load_index()

    def _load_index(self):
        """Load transaction index from file"""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                self.index = json.load(f)
        else:
            self.index = {"transactions": []}

    def _save_index(self):
        """Save transaction index to file"""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)

    def _generate_transaction_id(self) -> str:
        """Generate unique transaction ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"txn_{timestamp}"

    def create_transaction(
        self,
        transaction_id: Optional[str] = None,
        url: Optional[str] = None,
        extraction_mode: str = "links"
    ) -> str:
        """
        Create new transaction with unique ID.

        Args:
            transaction_id: Optional custom transaction ID
            url: URL being extracted
            extraction_mode: Type of extraction

        Returns:
            Transaction ID
        """
        if transaction_id is None:
            transaction_id = self._generate_transaction_id()

        # Create transaction directory
        txn_dir = self.data_dir / transaction_id
        txn_dir.mkdir(parents=True, exist_ok=True)

        # Create metadata
        metadata = {
            "transaction_id": transaction_id,
            "created_at": datetime.now().isoformat(),
            "url": url,
            "extraction_mode": extraction_mode,
            "status": "created"
        }

        # Save metadata
        self._save_metadata(transaction_id, metadata)

        # Add to index
        self.index["transactions"].append({
            "transaction_id": transaction_id,
            "created_at": metadata["created_at"],
            "url": url
        })
        self._save_index()

        return transaction_id

    def get_transaction_dir(self, transaction_id: str) -> Path:
        """Get path to transaction directory"""
        return self.data_dir / transaction_id

    def transaction_exists(self, transaction_id: str) -> bool:
        """Check if transaction exists"""
        return self.get_transaction_dir(transaction_id).exists()

    def save_html(
        self,
        transaction_id: str,
        raw_html: Optional[str] = None,
        sanitized_html: Optional[str] = None
    ):
        """
        Save HTML files for transaction.

        Args:
            transaction_id: Transaction ID
            raw_html: Original HTML (optional)
            sanitized_html: Sanitized HTML (optional)
        """
        txn_dir = self.get_transaction_dir(transaction_id)

        if raw_html is not None:
            with open(txn_dir / "raw.html", 'w', encoding='utf-8') as f:
                f.write(raw_html)

        if sanitized_html is not None:
            with open(txn_dir / "sanitized.html", 'w', encoding='utf-8') as f:
                f.write(sanitized_html)

    def save_elements(self, transaction_id: str, elements: List[Dict]):
        """
        Save element registry as JSON.

        Args:
            transaction_id: Transaction ID
            elements: List of element dictionaries
        """
        txn_dir = self.get_transaction_dir(transaction_id)
        with open(txn_dir / "elements.json", 'w', encoding='utf-8') as f:
            json.dump(elements, f, indent=2, ensure_ascii=False)

    def save_indexed_text(self, transaction_id: str, indexed_text: str):
        """
        Save indexed text format.

        Args:
            transaction_id: Transaction ID
            indexed_text: Indexed text representation
        """
        txn_dir = self.get_transaction_dir(transaction_id)
        with open(txn_dir / "indexed_text.txt", 'w', encoding='utf-8') as f:
            f.write(indexed_text)

    def _save_metadata(self, transaction_id: str, metadata: Dict):
        """Save transaction metadata"""
        txn_dir = self.get_transaction_dir(transaction_id)
        with open(txn_dir / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

    def update_metadata(self, transaction_id: str, updates: Dict):
        """
        Update transaction metadata.

        Args:
            transaction_id: Transaction ID
            updates: Dictionary of fields to update
        """
        metadata = self.get_metadata(transaction_id)
        metadata.update(updates)
        metadata["updated_at"] = datetime.now().isoformat()
        self._save_metadata(transaction_id, metadata)

    def get_metadata(self, transaction_id: str) -> Dict:
        """
        Retrieve transaction metadata.

        Args:
            transaction_id: Transaction ID

        Returns:
            Metadata dictionary
        """
        txn_dir = self.get_transaction_dir(transaction_id)
        metadata_file = txn_dir / "metadata.json"

        if not metadata_file.exists():
            raise ValueError(f"Transaction {transaction_id} not found")

        with open(metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_html(
        self,
        transaction_id: str,
        html_type: str = "sanitized"
    ) -> str:
        """
        Retrieve HTML for transaction.

        Args:
            transaction_id: Transaction ID
            html_type: Type of HTML ('raw' or 'sanitized')

        Returns:
            HTML content
        """
        txn_dir = self.get_transaction_dir(transaction_id)
        filename = f"{html_type}.html"
        html_file = txn_dir / filename

        if not html_file.exists():
            raise ValueError(f"{html_type} HTML not found for transaction {transaction_id}")

        with open(html_file, 'r', encoding='utf-8') as f:
            return f.read()

    def get_elements(self, transaction_id: str) -> List[Dict]:
        """
        Retrieve element registry for transaction.

        Args:
            transaction_id: Transaction ID

        Returns:
            List of element dictionaries
        """
        txn_dir = self.get_transaction_dir(transaction_id)
        elements_file = txn_dir / "elements.json"

        if not elements_file.exists():
            raise ValueError(f"Elements not found for transaction {transaction_id}")

        with open(elements_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_indexed_text(self, transaction_id: str) -> str:
        """
        Retrieve indexed text for transaction.

        Args:
            transaction_id: Transaction ID

        Returns:
            Indexed text content
        """
        txn_dir = self.get_transaction_dir(transaction_id)
        text_file = txn_dir / "indexed_text.txt"

        if not text_file.exists():
            raise ValueError(f"Indexed text not found for transaction {transaction_id}")

        with open(text_file, 'r', encoding='utf-8') as f:
            return f.read()

    def get_transaction(self, transaction_id: str) -> Dict:
        """
        Retrieve complete transaction data.

        Args:
            transaction_id: Transaction ID

        Returns:
            Dictionary with all transaction data
        """
        metadata = self.get_metadata(transaction_id)

        transaction_data = {
            "metadata": metadata,
            "has_raw_html": (self.get_transaction_dir(transaction_id) / "raw.html").exists(),
            "has_sanitized_html": (self.get_transaction_dir(transaction_id) / "sanitized.html").exists(),
            "has_elements": (self.get_transaction_dir(transaction_id) / "elements.json").exists(),
            "has_indexed_text": (self.get_transaction_dir(transaction_id) / "indexed_text.txt").exists()
        }

        return transaction_data

    def list_transactions(
        self,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        List all transactions.

        Args:
            limit: Maximum number of transactions to return
            offset: Number of transactions to skip

        Returns:
            List of transaction summaries
        """
        transactions = self.index["transactions"]

        # Sort by created_at descending (newest first)
        transactions = sorted(
            transactions,
            key=lambda x: x.get("created_at", ""),
            reverse=True
        )

        # Apply offset and limit
        if limit is not None:
            transactions = transactions[offset:offset + limit]
        else:
            transactions = transactions[offset:]

        # Enrich with element counts if available
        enriched = []
        for txn in transactions:
            txn_id = txn["transaction_id"]
            try:
                metadata = self.get_metadata(txn_id)
                enriched.append({
                    "transaction_id": txn_id,
                    "created_at": txn["created_at"],
                    "url": txn.get("url"),
                    "element_count": metadata.get("statistics", {}).get("total_elements", 0),
                    "status": metadata.get("status", "unknown")
                })
            except:
                enriched.append(txn)

        return enriched

    def delete_transaction(self, transaction_id: str):
        """
        Delete a transaction and all its data.

        Args:
            transaction_id: Transaction ID
        """
        import shutil

        txn_dir = self.get_transaction_dir(transaction_id)
        if txn_dir.exists():
            shutil.rmtree(txn_dir)

        # Remove from index
        self.index["transactions"] = [
            t for t in self.index["transactions"]
            if t["transaction_id"] != transaction_id
        ]
        self._save_index()


if __name__ == "__main__":
    # Test transaction manager
    import tempfile

    # Create temporary data directory
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = TransactionManager(tmpdir)

        # Create transaction
        txn_id = manager.create_transaction(
            url="https://example.com",
            extraction_mode="links"
        )
        print(f"Created transaction: {txn_id}")

        # Save data
        manager.save_html(
            txn_id,
            raw_html="<html><body>Test</body></html>",
            sanitized_html="<body>Test</body>"
        )

        manager.save_elements(txn_id, [
            {"tag": "a", "text": "Link 1", "href": "/page1"},
            {"tag": "a", "text": "Link 2", "href": "/page2"}
        ])

        manager.save_indexed_text(txn_id, "[0] <a>Link 1</a>\n[1] <a>Link 2</a>")

        # Update metadata
        manager.update_metadata(txn_id, {
            "statistics": {"total_elements": 2},
            "status": "completed"
        })

        # Retrieve data
        metadata = manager.get_metadata(txn_id)
        print(f"Metadata: {json.dumps(metadata, indent=2)}")

        elements = manager.get_elements(txn_id)
        print(f"Elements: {len(elements)}")

        # List transactions
        transactions = manager.list_transactions()
        print(f"Transactions: {len(transactions)}")

        print("✅ Transaction manager test passed!")
