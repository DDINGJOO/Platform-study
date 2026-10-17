package lab.lookup;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

/** ② 랜덤 IV(AES-GCM) 컨버터. 같은 평문이어도 부를 때마다 다른 암호문이 나온다 */
@Converter
public class GcmConverter implements AttributeConverter<String, String> {
    @Override public String convertToDatabaseColumn(String plain) { return plain == null ? null : Crypto.gcmEncrypt(plain); }
    @Override public String convertToEntityAttribute(String db) { return db == null ? null : Crypto.gcmDecrypt(db); }
}
