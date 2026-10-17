package lab.rollback;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "item")
public class Item {
    @Id
    Integer id;
    int v;

    protected Item() {}
}
