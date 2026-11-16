package czr.mcbridge.core;

/** A message didn't follow the protocol. */
public class ProtocolException extends Exception {
    public ProtocolException(String message) {
        super(message);
    }
}
