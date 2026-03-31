only display input in add form if there is relationship and a foreign key field

## Single referenced fk support
A single fk column because a single column can technically reference multiple foreign keys — though it's rare.

Real-World Analogy
Imagine a database design where a column like person_id could reference either a customers.id or employees.id depending on context. You'd need multiple foreign key constraints on the same column — SQLAlchemy allows for that.

Example:
```sql
ALTER TABLE bookings ADD CONSTRAINT fk1 FOREIGN KEY (person_id) REFERENCES customers(id);
ALTER TABLE bookings ADD CONSTRAINT fk2 FOREIGN KEY (person_id) REFERENCES employees(id);
```

This is legal in some DBMSs (though generally discouraged due to complexity), and SQLAlchemy mirrors that flexibility by allowing Column.foreign_keys to be a set of ForeignKey objects.