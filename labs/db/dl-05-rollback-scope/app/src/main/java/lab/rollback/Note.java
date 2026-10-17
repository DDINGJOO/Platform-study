package lab.rollback;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** 트랜잭션 안에서 잠금 문장보다 "앞에" 실행한 일. 롤백 범위를 이 행이 남았는지로 본다. */
@Entity
@Table(name = "note")
public class Note {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    Long id;
    String who;

    protected Note() {}
    Note(String who) { this.who = who; }
}
