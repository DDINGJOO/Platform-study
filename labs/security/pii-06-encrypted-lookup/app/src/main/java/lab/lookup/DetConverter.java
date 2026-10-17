package lab.lookup;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

/** ① 결정적 암호화 컨버터. 같은 평문이면 같은 암호문이 나온다 */
@Converter
public class DetConverter implements AttributeConverter<String, String> {
    @Override public String convertToDatabaseColumn(String plain) { return plain == null ? null : Crypto.detEncrypt(plain); }
    @Override public String convertToEntityAttribute(String db) { return db == null ? null : Crypto.detDecrypt(db); }
}
